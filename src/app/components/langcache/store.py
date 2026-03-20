from __future__ import annotations

from typing import cast

from openai import AsyncOpenAI
from redis.asyncio import Redis

from app.components.langcache.validator import AskResponse, CacheStats
from app.config import get_settings
from app.logger import get_component_logger
from app.redis import get_client, reset_async_clients
from langcache import LangCache

STATS_KEY = "langcache:stats"

logger = get_component_logger("langcache")
langcache_store: LangCacheStore | None = None
_lang_cache_client: LangCache | None = None
_openai_client: AsyncOpenAI | None = None


class LangCacheStore:
    def __init__(
        self,
        lang_cache: LangCache,
        redis: Redis,
        openai: AsyncOpenAI,
        *,
        similarity_threshold: float,
        model: str,
    ) -> None:
        self.lang_cache = lang_cache
        self.redis = redis
        self.openai = openai
        self.similarity_threshold = similarity_threshold
        self.model = model

    async def _ensure_stats(self) -> None:
        existing = await self.redis.hgetall(STATS_KEY)  # type: ignore[misc]
        if existing:
            return

        await self.redis.hset(  # type: ignore[misc]
            STATS_KEY,
            mapping={"requests": 0, "hits": 0, "misses": 0},
        )

    async def _increment_stats(self, field: str, amount: int = 1) -> None:
        await self.redis.hincrby(STATS_KEY, field, amount)  # type: ignore[misc]

    async def reset(self) -> None:
        await self.lang_cache.flush_async()
        await self.redis.delete(STATS_KEY)
        await self._ensure_stats()

    async def answer_question(self, question: str) -> AskResponse:
        await self._ensure_stats()
        await self._increment_stats("requests")

        result = await self.lang_cache.search_async(
            prompt=question,
            similarity_threshold=self.similarity_threshold,
        )

        if result.data:
            entry = result.data[0]
            await self._increment_stats("hits")

            logger.info(
                "semantic cache hit",
                extra={
                    "component": "langcache",
                    "question": question,
                    "entryId": entry.id,
                    "similarity": round(entry.similarity, 3),
                },
            )
            return AskResponse(
                question=question,
                answer=entry.response,
                cache_hit=True,
                source="cache",
                matched_prompt=entry.prompt,
                similarity=round(entry.similarity, 3),
                entry_id=entry.id,
            )

        answer = await self._call_llm(question)

        stored = await self.lang_cache.set_async(
            prompt=question,
            response=answer,
        )
        await self._increment_stats("misses")

        logger.info(
            "semantic cache miss – answered via LLM",
            extra={
                "component": "langcache",
                "question": question,
                "entryId": stored.entry_id,
                "model": self.model,
            },
        )
        return AskResponse(
            question=question,
            answer=answer,
            cache_hit=False,
            source="llm",
            entry_id=stored.entry_id,
        )

    async def _call_llm(self, question: str) -> str:
        response = await self.openai.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": question}],
        )
        return response.choices[0].message.content or ""

    async def stats(self) -> CacheStats:
        await self._ensure_stats()
        payload = await self.redis.hgetall(STATS_KEY)  # type: ignore[misc]
        requests = int(cast(str, payload.get("requests", "0")))
        hits = int(cast(str, payload.get("hits", "0")))
        misses = int(cast(str, payload.get("misses", "0")))
        hit_rate = hits / requests if requests > 0 else 0.0

        return CacheStats(
            requests=requests,
            hits=hits,
            misses=misses,
            entries=hits + misses,
            hit_rate=round(hit_rate, 3),
        )


def get_lang_cache_client() -> LangCache:
    global _lang_cache_client

    if _lang_cache_client is None:
        settings = get_settings()
        _lang_cache_client = LangCache(
            server_url=settings.langcache_api_url,
            cache_id=settings.langcache_cache_id,
            api_key=settings.langcache_api_key,
        )

    return _lang_cache_client


def get_openai_client() -> AsyncOpenAI:
    global _openai_client

    if _openai_client is None:
        settings = get_settings()
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    return _openai_client


def get_langcache_store() -> LangCacheStore:
    global langcache_store

    if langcache_store is None:
        settings = get_settings()
        langcache_store = LangCacheStore(
            get_lang_cache_client(),
            get_client(),
            get_openai_client(),
            similarity_threshold=settings.langcache_cache_threshold,
            model=settings.openai_model,
        )

    return langcache_store


def reset_langcache_store() -> None:
    global langcache_store, _lang_cache_client, _openai_client

    langcache_store = None
    _lang_cache_client = None
    _openai_client = None
    reset_async_clients()
