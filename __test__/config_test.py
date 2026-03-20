from collections.abc import Iterator

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_read_langcache_overrides(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LANGCACHE_API_URL", "https://langcache.example.com")
    monkeypatch.setenv("LANGCACHE_CACHE_ID", "test-cache-id")
    monkeypatch.setenv("LANGCACHE_API_KEY", "test-api-key")
    monkeypatch.setenv("LANGCACHE_CACHE_THRESHOLD", "0.75")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4-mini")

    settings = get_settings()

    assert settings.langcache_api_url == "https://langcache.example.com"
    assert settings.langcache_cache_id == "test-cache-id"
    assert settings.langcache_api_key == "test-api-key"
    assert settings.langcache_cache_threshold == 0.75
    assert settings.openai_api_key == "sk-test-key"
    assert settings.openai_model == "gpt-5.4-mini"
