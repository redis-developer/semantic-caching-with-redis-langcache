from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from langcache.models.cacheentry import CacheEntry
from langcache.models.searchresponse import SearchResponse
from langcache.models.searchstrategy import SearchStrategy
from langcache.models.setresponse import SetResponse

from app.components.langcache.store import reset_langcache_store
from app.main import app
from app.redis import get_sync_client

STATS_KEY = "langcache:stats"


class FakeLangCache:
    """In-memory LangCache stand-in for tests."""

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}

    async def __aenter__(self) -> FakeLangCache:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def search_async(
        self, *, prompt: str, similarity_threshold: float | None = None, **kwargs: Any
    ) -> SearchResponse:
        for entry_id, entry in self._entries.items():
            if entry["prompt"] == prompt:
                return SearchResponse(
                    data=[
                        CacheEntry(
                            id=entry_id,
                            prompt=entry["prompt"],
                            response=entry["response"],
                            attributes={},
                            similarity=1.0,
                            search_strategy=SearchStrategy.SEMANTIC,
                        )
                    ]
                )
        return SearchResponse(data=[])

    async def set_async(
        self, *, prompt: str, response: str, **kwargs: Any
    ) -> SetResponse:
        entry_id = str(uuid4())
        self._entries[entry_id] = {"prompt": prompt, "response": response}
        return SetResponse(entry_id=entry_id)

    async def flush_async(self) -> None:
        self._entries.clear()


redis = get_sync_client()

LLM_ANSWER = "To reset your password, go to Settings > Account > Reset Password."


def _reset_state(fake: FakeLangCache) -> None:
    reset_langcache_store()
    fake._entries.clear()
    redis.delete(STATS_KEY)


def _mock_openai() -> AsyncMock:
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value.choices = [
        AsyncMock(message=AsyncMock(content=LLM_ANSWER))
    ]
    return mock_client


def test_semantic_cache_miss_then_hit():
    fake = FakeLangCache()
    _reset_state(fake)
    mock_openai = _mock_openai()

    with (
        patch(
            "app.components.langcache.store.get_lang_cache_client", return_value=fake
        ),
        patch("app.main.get_lang_cache_client", return_value=fake),
        patch(
            "app.components.langcache.store.get_openai_client",
            return_value=mock_openai,
        ),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            first = client.post(
                "/api/langcache/ask",
                json={"question": "How do I reset my password?"},
            )
            second = client.post(
                "/api/langcache/ask",
                json={"question": "How do I reset my password?"},
            )
            stats = client.get("/api/langcache/stats")

    assert first.status_code == 200
    assert first.json()["cacheHit"] is False
    assert first.json()["source"] == "llm"
    assert first.json()["answer"] == LLM_ANSWER

    assert second.status_code == 200
    assert second.json()["cacheHit"] is True
    assert second.json()["source"] == "cache"
    assert second.json()["answer"] == first.json()["answer"]

    assert stats.status_code == 200
    assert stats.json()["requests"] == 2
    assert stats.json()["hits"] == 1
    assert stats.json()["misses"] == 1


def test_semantic_cache_stats_track_entries_and_hit_rate():
    fake = FakeLangCache()
    _reset_state(fake)
    mock_openai = _mock_openai()

    with (
        patch(
            "app.components.langcache.store.get_lang_cache_client", return_value=fake
        ),
        patch("app.main.get_lang_cache_client", return_value=fake),
        patch(
            "app.components.langcache.store.get_openai_client",
            return_value=mock_openai,
        ),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            client.post(
                "/api/langcache/ask",
                json={"question": "Where is my invoice?"},
            )
            client.post(
                "/api/langcache/ask",
                json={"question": "Where is my invoice?"},
            )
            response = client.get("/api/langcache/stats")

    assert response.status_code == 200
    payload = response.json()

    assert payload["entries"] == 2
    assert payload["requests"] == 2
    assert payload["hits"] == 1
    assert payload["misses"] == 1
    assert payload["hitRate"] == 0.5
