import os
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest
from pytest_asyncio import is_async_test

ROOT = Path(__file__).resolve().parents[1]


def _redis_is_reachable(redis_url: str) -> bool:
    parsed = urlparse(redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379

    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _should_manage_local_redis(redis_url: str) -> bool:
    parsed = urlparse(redis_url)
    return parsed.hostname in {None, "localhost", "127.0.0.1"} and (
        parsed.port in {None, 6379}
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_test_redis():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    started_local_redis = False

    if _should_manage_local_redis(redis_url) and not _redis_is_reachable(redis_url):
        subprocess.run(
            ["docker", "compose", "up", "redis", "-d"],
            cwd=ROOT,
            check=True,
        )
        started_local_redis = True

    yield

    if started_local_redis:
        subprocess.run(
            ["docker", "compose", "stop", "redis"],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            ["docker", "compose", "rm", "-f", "redis"],
            cwd=ROOT,
            check=True,
        )


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")

    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)
