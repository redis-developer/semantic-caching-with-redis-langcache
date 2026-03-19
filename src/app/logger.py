import json
import logging
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime
from logging import LogRecord
from typing import Any, cast

from redis import Redis as SyncRedis

from app.config import get_settings

_configured = False


class ComponentLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    def process(
        self, msg: object, kwargs: MutableMapping[str, Any]
    ) -> tuple[object, MutableMapping[str, Any]]:
        extra: dict[str, Any] = {}

        if self.extra is not None:
            extra.update(cast(Mapping[str, Any], self.extra))

        extra.update(cast(Mapping[str, Any], kwargs.get("extra", {})))
        kwargs["extra"] = extra
        return msg, kwargs


def _record_metadata(record: LogRecord) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "logger": record.name,
    }
    for key, value in record.__dict__.items():
        if key in {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
        }:
            continue

        metadata[key] = value

    if record.exc_info:
        metadata["exception"] = logging.Formatter().formatException(record.exc_info)

    return metadata


class ConsoleFormatter(logging.Formatter):
    def format(self, record: LogRecord) -> str:
        settings = get_settings()
        metadata = _record_metadata(record)
        base = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "component": getattr(record, "component", "root"),
            "msg": record.getMessage(),
        }

        if settings.is_production:
            return json.dumps({**base, "metadata": metadata}, default=str)

        if metadata:
            return (
                f"[{base['time']}] {record.levelname} "
                f"({base['component']}): {base['msg']} {json.dumps(metadata, default=str)}"
            )

        return (
            f"[{base['time']}] {record.levelname} ({base['component']}): {base['msg']}"
        )


class RedisStreamHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        settings = get_settings()
        self.stream_key = settings.log_stream_key
        self.redis = SyncRedis.from_url(
            settings.redis_url,
            decode_responses=True,
            health_check_interval=1,
        )

    def emit(self, record: LogRecord) -> None:
        payload = {
            "level": record.levelname.lower(),
            "component": str(getattr(record, "component", "root")),
            "msg": record.getMessage(),
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "metadata": json.dumps(_record_metadata(record), default=str),
        }

        try:
            self.redis.xadd(self.stream_key, cast(Any, payload))
        except Exception:
            # Logging to Redis is best-effort and must not break requests.
            return


def configure_logging() -> None:
    global _configured

    if _configured:
        return

    settings = get_settings()
    app_logger = logging.getLogger("app")
    app_logger.handlers.clear()
    app_logger.setLevel(settings.log_level)
    app_logger.propagate = False

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ConsoleFormatter())
    app_logger.addHandler(console_handler)
    app_logger.addHandler(RedisStreamHandler())

    _configured = True


def get_logger(name: str = "app") -> logging.Logger:
    configure_logging()
    logger = logging.getLogger(name)
    logger.setLevel(get_settings().log_level)
    return logger


def get_component_logger(component: str) -> ComponentLoggerAdapter:
    return ComponentLoggerAdapter(get_logger(), {"component": component})


logger = get_logger()
