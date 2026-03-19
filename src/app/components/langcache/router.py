from typing import Any

from fastapi import APIRouter

from app.components.langcache import controller

router = APIRouter()


@router.post("/ask", tags=["langcache"])
async def ask(body: dict[str, Any]) -> dict[str, Any]:
    """Answers a question using semantic cache lookup and fallback generation."""
    response = await controller.ask(body)
    return response.model_dump(by_alias=True)


@router.get("/stats", tags=["langcache"])
async def stats() -> dict[str, Any]:
    """Returns cache hit and miss statistics."""
    response = await controller.stats()
    return response.model_dump(by_alias=True)

