# app/core/middleware.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import time

from fastapi import FastAPI, Request

from app.core.config import get_settings
from app.core.context import clear_request_context, set_request_meta
from app.core.logger import get_logger
from app.core.trace import resolve_trace_id

logger = get_logger(__name__)


def register_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def trace_middleware(request: Request, call_next):
        settings = get_settings()

        trace_id = resolve_trace_id(request)
        set_request_meta(request.method, request.url.path)

        start = time.perf_counter()
        logger.info("请求进入")

        try:
            response = await call_next(request)
            response.headers[settings.trace_header_name] = trace_id
            return response
        except Exception:
            logger.exception("请求处理异常")
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info("请求结束, cost_ms=%s", elapsed_ms)
            clear_request_context()