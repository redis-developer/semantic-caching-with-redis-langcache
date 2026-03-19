from redis import Redis as SyncRedis
from redis.asyncio import Redis
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError
from redis.retry import Retry

from app.config import get_settings

async_clients: dict[str, Redis] = {}
sync_clients: dict[str, SyncRedis] = {}


def _resolve_url(url: str | None) -> str:
    return url if url is not None else get_settings().redis_url


def get_client(url: str | None = None) -> Redis:
    redis_url = _resolve_url(url)

    if redis_url in async_clients:
        return async_clients[redis_url]

    async_clients[redis_url] = Redis.from_url(
        redis_url,
        decode_responses=True,
        retry=Retry(ExponentialBackoff(cap=10, base=1), 25),
        retry_on_error=[ConnectionError, TimeoutError, ConnectionResetError],
        health_check_interval=1,
    )

    return async_clients[redis_url]


def get_sync_client(url: str | None = None) -> SyncRedis:
    redis_url = _resolve_url(url)

    if redis_url in sync_clients:
        return sync_clients[redis_url]

    sync_clients[redis_url] = SyncRedis.from_url(
        redis_url,
        decode_responses=True,
        health_check_interval=1,
    )

    return sync_clients[redis_url]


async def close_async_clients() -> None:
    for client in async_clients.values():
        await client.aclose()
    async_clients.clear()


def reset_async_clients() -> None:
    async_clients.clear()
