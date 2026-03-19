from fastapi.testclient import TestClient
from redis.exceptions import ResponseError

from app.components.langcache.store import reset_langcache_store
from app.config import get_settings
from app.main import app
from app.redis import get_sync_client

settings = get_settings()
redis = get_sync_client()
CACHE_PREFIX = "langcache:entry:"
STATS_KEY = "langcache:stats"


def _reset_cache_state() -> None:
    reset_langcache_store()
    cache_keys = redis.keys(f"{CACHE_PREFIX}*")

    if len(cache_keys) > 0:
        redis.delete(*cache_keys)

    redis.delete(STATS_KEY)

    try:
        redis.ft("langcache-idx").dropindex()
    except ResponseError as exc:
        if "Unknown index name" not in str(exc) and "no such index" not in str(exc):
            raise


def _stats_snapshot() -> dict[str, str]:
    return redis.hgetall(STATS_KEY)


def test_semantic_cache_hits_on_follow_up_question():
    _reset_cache_state()

    with TestClient(app, raise_server_exceptions=False) as client:

        first = client.post(
            "/api/langcache/ask",
            json={"question": "How do I reset my password?"},
        )
        second = client.post(
            "/api/langcache/ask",
            json={"question": "I forgot how to change my login password."},
        )
        stats = client.get("/api/langcache/stats")

    assert first.status_code == 200
    assert first.json()["cacheHit"] is False
    assert first.json()["source"] == "fallback"
    assert first.json()["matchedPrompt"] == "How do I reset my password?"

    assert second.status_code == 200
    assert second.json()["cacheHit"] is True
    assert second.json()["source"] == "cache"
    assert second.json()["answer"] == first.json()["answer"]

    assert stats.status_code == 200
    assert stats.json()["requests"] == 2
    assert stats.json()["hits"] == 1
    assert stats.json()["misses"] == 1


def test_semantic_cache_stats_track_entries_and_hit_rate():
    _reset_cache_state()

    with TestClient(app, raise_server_exceptions=False) as client:

        client.post("/api/langcache/ask", json={"question": "Where is my invoice?"})
        client.post(
            "/api/langcache/ask",
            json={"question": "Show me my billing receipt."},
        )
        response = client.get("/api/langcache/stats")

    assert response.status_code == 200
    payload = response.json()

    assert payload["entries"] == 1
    assert payload["requests"] == 2
    assert payload["hits"] == 1
    assert payload["misses"] == 1
    assert payload["hitRate"] == 0.5
