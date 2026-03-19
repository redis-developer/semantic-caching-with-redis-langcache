from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.components.langcache.router import router as langcache_router
from app.errors import ClientError
from app.logger import configure_logging, get_logger
from app.redis import close_async_clients


def _validation_message(exc: ValidationError | RequestValidationError) -> str:
    return ", ".join(error["msg"] for error in exc.errors())


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield
    await close_async_clients()


app = FastAPI(lifespan=lifespan)
logger = get_logger()


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next: Any) -> Any:
    start = perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration_ms = round((perf_counter() - start) * 1000, 2)
        client = request.client
        logger.info(
            "request completed",
            extra={
                "req": {
                    "method": request.method,
                    "url": str(request.url.path),
                    "query": dict(request.query_params),
                    "params": dict(request.path_params),
                    "headers": dict(request.headers),
                    "remoteAddress": client.host if client else None,
                    "remotePort": client.port if client else None,
                },
                "statusCode": status_code,
                "responseTime": duration_ms,
            },
        )


@app.exception_handler(ClientError)
async def client_error_handler(_: Request, exc: ClientError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={"status": exc.status, "message": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"status": 400, "message": _validation_message(exc)},
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(_: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"status": 400, "message": _validation_message(exc)},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", extra={"error": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"status": 500, "message": "Internal Server Error"},
    )


app.include_router(router=langcache_router, prefix="/api/langcache")
