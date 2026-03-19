from collections.abc import Iterator

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_read_langcache_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LANGCACHE_TTL_SECONDS", "120")
    monkeypatch.setenv("LANGCACHE_CACHE_THRESHOLD", "0.75")
    monkeypatch.setenv("LANGCACHE_KNOWLEDGE_THRESHOLD", "0.25")

    settings = get_settings()

    assert settings.langcache_ttl_seconds == 120
    assert settings.langcache_cache_threshold == 0.75
    assert settings.langcache_knowledge_threshold == 0.25

