from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator
from pydantic_core import PydanticCustomError

from app.components.todos.store import TodoStatus


class CreateTodoBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if len(value) == 0:
            raise PydanticCustomError("todo_name", "Todo must have a name")

        return value


class UpdateTodoBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: TodoStatus


class SearchTodosQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    status: TodoStatus | None = None


class TodoIdParams(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Annotated[str, StringConstraints(min_length=1)]
