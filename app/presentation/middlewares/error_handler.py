from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import DomainError, WarehouseNotFoundError
from app.core.logging import logger

def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers implementing RFC 7807 Problem Details."""

    @app.exception_handler(WarehouseNotFoundError)
    async def warehouse_not_found_handler(
        request: Request, exc: WarehouseNotFoundError
    ) -> JSONResponse:
        logger.warn("warehouse_not_found", warehouse_id=exc.warehouse_id, path=request.url.path)
        content: dict[str, Any] = {
            "type": "https://errors.warehouse-manager.io/not-found",
            "title": "Resource Not Found",
            "status": status.HTTP_404_NOT_FOUND,
            "detail": str(exc),
            "instance": request.url.path,
        }
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=content)

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        logger.warn("domain_error", error=str(exc), path=request.url.path)
        content: dict[str, Any] = {
            "type": "https://errors.warehouse-manager.io/domain-error",
            "title": "Domain Rule Violation",
            "status": status.HTTP_400_BAD_REQUEST,
            "detail": str(exc),
            "instance": request.url.path,
        }
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warn("validation_error", errors=exc.errors(), path=request.url.path)
        content: dict[str, Any] = {
            "type": "https://errors.warehouse-manager.io/validation-error",
            "title": "Validation Error",
            "status": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "detail": "The request payload failed input schema validation.",
            "instance": request.url.path,
            "invalid_params": exc.errors(),
        }
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=content)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        content: dict[str, Any] = {
            "type": "https://errors.warehouse-manager.io/http-error",
            "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "status": exc.status_code,
            "detail": str(exc.detail),
            "instance": request.url.path,
        }
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_server_error", error=str(exc), path=request.url.path)
        content: dict[str, Any] = {
            "type": "https://errors.warehouse-manager.io/internal-error",
            "title": "Internal Server Error",
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "An unexpected error occurred while processing the request.",
            "instance": request.url.path,
        }
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=content)