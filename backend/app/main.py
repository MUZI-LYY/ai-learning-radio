"""FastAPI 应用入口。

统一错误结构、CORS、健康检查；日志只记录错误类型与 request_id，不泄露堆栈给前端。
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode, ensure_error_meta
from app.core.logging import configure_logging

logger = logging.getLogger("app.main")


def _error_content(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": str(uuid.uuid4())}}


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    allowed_origins = [settings.frontend_origin]
    if settings.is_development:
        allowed_origins.extend(
            ["http://127.0.0.1:3001", "http://localhost:3001"]
        )
    allowed_origins = list(dict.fromkeys(allowed_origins))

    app = FastAPI(
        title="AI 学习电台 API", version="0.1.0", docs_url="/docs", openapi_url="/openapi.json"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=_error_content(exc.code, exc.message)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        status, default_message = ensure_error_meta(ErrorCode.INVALID_REQUEST)
        return JSONResponse(
            status_code=status,
            content=_error_content(ErrorCode.INVALID_REQUEST, default_message),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s", request.url.path)
        status, default_message = ensure_error_meta(ErrorCode.INTERNAL_ERROR)
        return JSONResponse(
            status_code=status,
            content=_error_content(ErrorCode.INTERNAL_ERROR, default_message),
        )

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(api_router)
    return app


app = create_app()
