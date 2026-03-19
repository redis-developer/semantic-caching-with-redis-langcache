import re
from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast
from uuid import uuid4

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic_core import from_json
from redis.asyncio import Redis
from redis.commands.search.document import Document
from redis.commands.search.field import Field as SearchField
from redis.commands.search.field import TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError

from app.errors import ClientError
from app.logger import get_component_logger
from app.redis import get_client, reset_async_clients

TODOS_INDEX = "todos-idx"
TODOS_PREFIX = "todos:"
logger = get_component_logger("todos")
todos_store: "TodoStore | None" = None


class TodoStatus(str, Enum):
    todo = "todo"
    in_progress = "in progress"
    complete = "complete"


class Todo(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    name: str
    status: TodoStatus
    created_date: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("createdDate", "created_date"),
        serialization_alias="createdDate",
    )
    updated_date: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("updatedDate", "updated_date"),
        serialization_alias="updatedDate",
    )


class TodoDocument(BaseModel):
    id: str
    value: Todo


class Todos(BaseModel):
    total: int
    documents: list[TodoDocument]


class TodoStore:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.index = TODOS_INDEX
        self.prefix = TODOS_PREFIX

    async def initialize(self) -> None:
        await self.create_index_if_not_exists()

    async def have_index(self) -> bool:
        try:
            await self.redis.ft(self.index).info()
        except ResponseError as exc:
            if "Unknown index name" in str(exc) or "no such index" in str(exc):
                logger.debug(f"Index {self.index} does not exist")
                return False

        logger.debug(f"Index {self.index} already exists")
        return True

    async def create_index_if_not_exists(self) -> None:
        if await self.have_index():
            return

        logger.debug(f"Creating index {self.index}")
        schema: list[SearchField] = [
            TextField("$.name", as_name="name"),
            TextField("$.status", as_name="status"),
        ]

        try:
            await self.redis.ft(self.index).create_index(
                schema,
                definition=IndexDefinition(
                    prefix=[TODOS_PREFIX],
                    index_type=IndexType.JSON,
                ),
            )
        except Exception as exc:
            logger.error(f"Error setting up index {self.index}: {exc}")
            raise

    async def drop_index(self) -> None:
        if not await self.have_index():
            return

        try:
            await self.redis.ft(self.index).dropindex()
        except Exception as exc:
            logger.error(f"Error dropping index {self.index}: {exc}")
            raise

    def format_id(self, todo_id: str) -> str:
        if re.match(f"^{self.prefix}", todo_id):
            return todo_id

        return f"{self.prefix}{todo_id}"

    def deserialize_todo_document(self, todo: Document) -> TodoDocument:
        return TodoDocument(
            id=todo.id,
            value=Todo.model_validate(
                from_json(
                    cast(str, cast(Any, todo).json),
                    allow_partial=True,
                )
            ),
        )

    def deserialize_todo_documents(self, todos: list[Document]) -> list[TodoDocument]:
        return [self.deserialize_todo_document(doc) for doc in todos]

    async def all(self) -> Todos:
        try:
            result = await self.redis.ft(self.index).search("*")
        except Exception as exc:
            logger.error(f"Error getting all todos: {exc}")
            raise

        return Todos(
            total=result.total,
            documents=self.deserialize_todo_documents(result.docs),
        )

    async def one(self, todo_id: str) -> Todo:
        formatted_id = self.format_id(todo_id)

        try:
            # redis-py async JSON stubs are currently typed as sync returns.
            payload = cast(
                dict[str, object] | None,
                await self.redis.json().get(formatted_id),  # type: ignore[misc]
            )
        except Exception as exc:
            logger.error(f"Error getting todo {formatted_id}: {exc}")
            raise

        if payload is None:
            raise ClientError(404, "Not Found")

        return Todo.model_validate(payload)

    async def search(self, name: str | None, status: TodoStatus | None) -> Todos:
        searches: list[str] = []

        if name is not None and len(name) > 0:
            searches.append(f"@name:({name})")

        if status is not None:
            searches.append(f'@status:"{status.value}"')

        try:
            result = await self.redis.ft(self.index).search(Query(" ".join(searches)))
        except Exception as exc:
            logger.error(f"Error searching todos: {exc}")
            raise

        return Todos(
            total=result.total,
            documents=self.deserialize_todo_documents(result.docs),
        )

    async def create(self, todo_id: str | None, name: str | None) -> TodoDocument:
        if name is None:
            raise ClientError(400, "Todo must have a name")

        created_at = datetime.now(UTC)
        todo = TodoDocument(
            id=self.format_id(todo_id or str(uuid4())),
            value=Todo(
                name=name,
                status=TodoStatus.todo,
                created_date=created_at,
                updated_date=created_at,
            ),
        )

        try:
            result = await self.redis.json().set(
                todo.id,
                "$",
                todo.value.model_dump(by_alias=True, exclude_none=True, mode="json"),
            )  # type: ignore[misc]
        except Exception as exc:
            logger.error(f"Error creating todo {todo.id}: {exc}")
            raise

        if result not in {True, "OK"}:
            raise ClientError(400, "Todo is invalid")

        return todo

    async def update(self, todo_id: str, status: TodoStatus) -> Todo:
        updated_at = datetime.now(UTC)
        todo = await self.one(todo_id)
        todo.status = status
        todo.updated_date = updated_at

        try:
            result = await self.redis.json().set(
                self.format_id(todo_id),
                "$",
                todo.model_dump(by_alias=True, exclude_none=True, mode="json"),
            )  # type: ignore[misc]
        except Exception as exc:
            logger.error(f"Error updating todo {todo_id}: {exc}")
            raise

        if result not in {True, "OK"}:
            raise ClientError(400, "Todo is invalid")

        return todo

    async def delete(self, todo_id: str) -> None:
        try:
            await self.redis.json().delete(self.format_id(todo_id))  # type: ignore[misc]
        except Exception as exc:
            logger.error(f"Error deleting todo {todo_id}: {exc}")
            raise

    async def delete_all(self) -> None:
        todos = await self.all()

        for todo in todos.documents:
            try:
                await self.redis.json().delete(todo.id)  # type: ignore[misc]
            except Exception as exc:
                logger.error(f"Error deleting todos: {exc}")
                raise


def get_todos_store() -> TodoStore:
    global todos_store

    if todos_store is None:
        todos_store = TodoStore(get_client())

    return todos_store


def reset_todos_store() -> None:
    global todos_store

    todos_store = None
    reset_async_clients()
