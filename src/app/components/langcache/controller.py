from typing import Any

from app.components.langcache.store import get_langcache_store
from app.components.langcache.validator import AskQuestionBody, AskResponse, CacheStats
from app.logger import get_component_logger

logger = get_component_logger("langcache")


async def initialize() -> None:
    return None


async def ask(body: dict[str, Any]) -> AskResponse:
    parsed = AskQuestionBody.model_validate(body)
    logger.debug("Answering question", extra={"question": parsed.question})
    return await get_langcache_store().answer_question(parsed.question)


async def stats() -> CacheStats:
    logger.debug("Reading semantic cache stats")
    return await get_langcache_store().stats()
