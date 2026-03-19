from typing import Any

from fastapi import APIRouter, Request, Response

from app.components.todos import controller
from app.components.todos.store import Todo, TodoDocument, Todos

router = APIRouter()


@router.get("", tags=["todos"])
async def all() -> Todos:
    """Gets all todos"""
    return await controller.get_all()


@router.get("/search", tags=["todos"])
async def search(request: Request) -> Todos:
    """Searches for todos by name and/or status"""
    return await controller.search(dict(request.query_params))


@router.get("/{id}", tags=["todos"])
async def one(id: str) -> Todo:
    """Gets a todo by id"""
    return await controller.get_one({"id": id})


@router.post("", tags=["todos"])
async def create(todo: dict[str, Any]) -> TodoDocument:
    """Creates a todo"""
    return await controller.create(todo)


@router.patch("/{id}", tags=["todos"])
async def update(id: str, todo: dict[str, Any]) -> Todo:
    """Updates a todo's status"""
    return await controller.update({"id": id}, todo)


@router.delete("/{id}", tags=["todos"])
async def delete(id: str) -> Response:
    """Deletes a todo"""
    await controller.delete({"id": id})
    return Response(status_code=200)
