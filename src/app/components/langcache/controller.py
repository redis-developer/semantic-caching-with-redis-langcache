from app.components.langcache.store import get_langcache_store
from app.components.langcache.validator import AskResponse, CacheStats
from app.logger import get_component_logger

logger = get_component_logger("langcache")


async def ask(question: str) -> AskResponse:
    logger.debug("Answering question", extra={"question": question})
    return await get_langcache_store().answer_question(question)


async def stats() -> CacheStats:
    logger.debug("Reading semantic cache stats")
    return await get_langcache_store().stats()
