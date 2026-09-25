from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.infrastructure.cache.redis_client import close_redis_client, get_redis_client
from app.infrastructure.database.session import async_session_factory, engine
from app.presentation.api.v1.router import api_v1_router
from app.presentation.middlewares.correlation_id import CorrelationIdMiddleware
from app.presentation.middlewares.error_handler import register_exception_handlers


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager handling startup and shutdown hooks."""
    setup_logging()
    logger.info("application_startup", environment=settings.ENVIRONMENT)
    yield
    logger.info("application_shutdown")
    await close_redis_client()
    await engine.dispose()


def create_app() -> FastAPI:
    """FastAPI application factory with middlewares, routers, and telemetry."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="Operations Research Spatial Optimization Engine for Coffee Warehouses",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app)

    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    @app.get(
        "/health",
        tags=["System"],
        summary="Service Health Check",
        description="Probes PostgreSQL and Redis connections.",
    )
    async def health_check() -> JSONResponse:
        db_status = "down"
        redis_status = "down"

        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
                db_status = "up"
        except Exception as e:
            logger.warn("health_db_check_failed", error=str(e))

        # Check Redis
        try:
            client = await get_redis_client()
            await client.ping()
            redis_status = "up"
        except Exception as e:
            logger.warn("health_redis_check_failed", error=str(e))

        is_healthy = db_status == "up" and redis_status == "up"
        http_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        content: dict[str, Any] = {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "services": {
                "database": db_status,
                "redis": redis_status,
            },
        }
        return JSONResponse(status_code=http_status, content=content)

    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    return app


app = create_app()
