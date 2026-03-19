from typing import Any

from app.components.todos.store import Todo, TodoDocument, Todos, get_todos_store
from app.components.todos.validator import (
    CreateTodoBody,
    SearchTodosQuery,
    TodoIdParams,
    UpdateTodoBody,
)
from app.logger import get_component_logger

logger = get_component_logger("todos")


async def initialize() -> None:
    await get_todos_store().initialize()


async def get_all() -> Todos:
    logger.debug("Fetching all todos")
    return await get_todos_store().all()


async def search(query: dict[str, Any]) -> Todos:
    parsed = SearchTodosQuery.model_validate(query)
    logger.debug(
        "Searching todos",
        extra={
            "queryName": parsed.name,
            "status": parsed.status.value if parsed.status else None,
        },
    )
    return await get_todos_store().search(parsed.name, parsed.status)


async def get_one(params: dict[str, Any]) -> Todo:
    parsed = TodoIdParams.model_validate(params)
    logger.debug("Fetching todo", extra={"id": parsed.id})
    return await get_todos_store().one(parsed.id)


async def create(body: dict[str, Any]) -> TodoDocument:
    parsed = CreateTodoBody.model_validate(body)
    logger.debug("Creating todo", extra={"id": parsed.id, "todoName": parsed.name})
    return await get_todos_store().create(parsed.id, parsed.name)


async def update(params: dict[str, Any], body: dict[str, Any]) -> Todo:
    parsed_params = TodoIdParams.model_validate(params)
    parsed_body = UpdateTodoBody.model_validate(body)
    logger.debug(
        "Updating todo",
        extra={"id": parsed_params.id, "status": parsed_body.status.value},
    )
    return await get_todos_store().update(parsed_params.id, parsed_body.status)


async def delete(params: dict[str, Any]) -> None:
    parsed = TodoIdParams.model_validate(params)
    logger.debug("Deleting todo", extra={"id": parsed.id})
    await get_todos_store().delete(parsed.id)
