from typing import Any

from fastapi import APIRouter

from app.components.langcache import controller
from app.components.langcache.validator import AskQuestionBody

router = APIRouter()


@router.post("/ask", tags=["langcache"])
async def ask(body: AskQuestionBody) -> dict[str, Any]:
    """Answers a question using semantic cache lookup and fallback generation."""
    response = await controller.ask(body.question)
    return response.model_dump(by_alias=True)


@router.get("/stats", tags=["langcache"])
async def stats() -> dict[str, Any]:
    """Returns cache hit and miss statistics."""
    response = await controller.stats()
    return response.model_dump(by_alias=True)
