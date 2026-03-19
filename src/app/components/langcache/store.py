from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from redis.asyncio import Redis

from app.components.langcache.embedding import cosine_similarity, embed_text
from app.components.langcache.knowledge_base import choose_best_knowledge_answer
from app.components.langcache.validator import AskResponse, CacheStats
from app.config import get_settings
from app.logger import get_component_logger
from app.redis import get_client, reset_async_clients

CACHE_PREFIX = "langcache:entry:"
STATS_KEY = "langcache:stats"

logger = get_component_logger("langcache")
langcache_store: LangCacheStore | None = None


class LangCacheStore:
    def __init__(
        self,
        redis: Redis,
        *,
        ttl_seconds: int,
        cache_threshold: float,
        knowledge_threshold: float,
    ) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds
        self.cache_threshold = cache_threshold
        self.knowledge_threshold = knowledge_threshold

    async def _ensure_stats(self) -> None:
        existing = await self.redis.hgetall(STATS_KEY)
        if existing:
            return

        await self.redis.hset(
            STATS_KEY,
            mapping={"requests": 0, "hits": 0, "misses": 0},
        )

    async def reset(self) -> None:
        keys = await self.redis.keys(f"{CACHE_PREFIX}*")
        if len(keys) > 0:
            await self.redis.delete(*keys)

        await self.redis.delete(STATS_KEY)
        await self._ensure_stats()

    async def _load_entries(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        keys = await self.redis.keys(f"{CACHE_PREFIX}*")
        if len(keys) == 0:
            return entries

        async with self.redis.pipeline() as pipeline:
            for key in keys:
                pipeline.hgetall(key)

            results = await pipeline.execute()

        for key, payload in zip(keys, results, strict=True):
            if not payload:
                continue

            entry = dict(payload)
            entry["cache_key"] = key
            entry["question_embedding"] = _parse_embedding(
                cast(str, entry["question_embedding"])
            )
            entry["hit_count"] = int(cast(str, entry.get("hit_count", "0")))
            entry["similarity"] = float(cast(str, entry.get("similarity", "0")))
            entries.append(entry)

        return entries

    async def _increment_stats(self, field: str, amount: int = 1) -> None:
        await self.redis.hincrby(STATS_KEY, field, amount)

    async def _save_entry(
        self,
        *,
        question: str,
        answer: str,
        embedding: list[float],
        matched_prompt: str | None,
        similarity: float,
    ) -> tuple[str, int]:
        created_at = datetime.now(UTC).isoformat()
        cache_key = f"{CACHE_PREFIX}{uuid4()}"

        await self.redis.hset(
            cache_key,
            mapping={
                "question": question,
                "answer": answer,
                "matched_prompt": matched_prompt or "",
                "similarity": similarity,
                "question_embedding": _serialize_embedding(embedding),
                "created_at": created_at,
                "updated_at": created_at,
                "last_hit_at": "",
                "hit_count": 0,
            },
        )
        await self.redis.expire(cache_key, self.ttl_seconds)
        return cache_key, 0

    async def answer_question(self, question: str) -> AskResponse:
        await self._ensure_stats()
        await self._increment_stats("requests")

        question_embedding = embed_text(question)
        best_entry: dict[str, Any] | None = None
        best_similarity = 0.0

        for entry in await self._load_entries():
            similarity = cosine_similarity(
                question_embedding,
                cast(list[float], entry["question_embedding"]),
            )
            if similarity > best_similarity:
                best_similarity = similarity
                best_entry = entry

        if best_entry is not None and best_similarity >= self.cache_threshold:
            hit_count = int(cast(int | str, best_entry["hit_count"])) + 1
            now = datetime.now(UTC).isoformat()
            await self.redis.hset(
                best_entry["cache_key"],
                mapping={
                    "hit_count": hit_count,
                    "last_hit_at": now,
                    "updated_at": now,
                },
            )
            await self._increment_stats("hits")

            logger.info(
                "semantic cache hit",
                extra={
                    "component": "langcache",
                    "question": question,
                    "cacheKey": best_entry["cache_key"],
                    "similarity": round(best_similarity, 3),
                },
            )
            return AskResponse(
                question=question,
                answer=cast(str, best_entry["answer"]),
                cache_hit=True,
                source="cache",
                matched_prompt=cast(str, best_entry["matched_prompt"]) or None,
                similarity=round(best_similarity, 3),
                cache_key=cast(str, best_entry["cache_key"]),
                ttl_seconds=self.ttl_seconds,
                hit_count=hit_count,
            )

        answer, matched_prompt, fallback_similarity = self._generate_answer(question)
        cache_key, hit_count = await self._save_entry(
            question=question,
            answer=answer,
            embedding=question_embedding,
            matched_prompt=matched_prompt,
            similarity=round(fallback_similarity, 3),
        )
        await self._increment_stats("misses")

        logger.info(
            "semantic cache miss",
            extra={
                "component": "langcache",
                "question": question,
                "cacheKey": cache_key,
                "matchedPrompt": matched_prompt,
                "similarity": round(fallback_similarity, 3),
            },
        )
        return AskResponse(
            question=question,
            answer=answer,
            cache_hit=False,
            source="fallback",
            matched_prompt=matched_prompt,
            similarity=round(fallback_similarity, 3),
            cache_key=cache_key,
            ttl_seconds=self.ttl_seconds,
            hit_count=hit_count,
        )

    def _generate_answer(self, question: str) -> tuple[str, str | None, float]:
        entry, similarity = choose_best_knowledge_answer(question)
        if entry is not None and similarity >= self.knowledge_threshold:
            return entry.answer, entry.prompt, similarity

        return (
            "I could not find a close answer yet, but I have logged the question for follow-up.",
            None,
            similarity,
        )

    async def stats(self) -> CacheStats:
        await self._ensure_stats()
        payload = await self.redis.hgetall(STATS_KEY)
        requests = int(cast(str, payload.get("requests", "0")))
        hits = int(cast(str, payload.get("hits", "0")))
        misses = int(cast(str, payload.get("misses", "0")))
        entries = len(await self.redis.keys(f"{CACHE_PREFIX}*"))
        hit_rate = hits / requests if requests > 0 else 0.0

        return CacheStats(
            requests=requests,
            hits=hits,
            misses=misses,
            entries=entries,
            hit_rate=round(hit_rate, 3),
        )


def _serialize_embedding(embedding: list[float]) -> str:
    return ",".join(f"{value:.6f}" for value in embedding)


def _parse_embedding(serialized_embedding: str) -> list[float]:
    if len(serialized_embedding) == 0:
        return []

    return [float(part) for part in serialized_embedding.split(",")]


def get_langcache_store() -> LangCacheStore:
    global langcache_store

    if langcache_store is None:
        settings = get_settings()
        langcache_store = LangCacheStore(
            get_client(),
            ttl_seconds=settings.langcache_ttl_seconds,
            cache_threshold=settings.langcache_cache_threshold,
            knowledge_threshold=settings.langcache_knowledge_threshold,
        )

    return langcache_store


def reset_langcache_store() -> None:
    global langcache_store

    langcache_store = None
    reset_async_clients()
