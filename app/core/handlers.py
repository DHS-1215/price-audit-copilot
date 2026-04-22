# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 14:37
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException, ErrorCodes
from app.core.logger import get_logger
from app.core.response import error_response
from app.core.trace import get_trace_id

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "应用异常: code=%s detail=%s path=%s",
            exc.error_code.code,
            exc.detail,
            request.url.path,
        )
        payload = error_response(
            code=exc.error_code.code,
            message=exc.detail,
            trace_id=get_trace_id(),
            data=exc.extra or None,
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("请求校验失败: path=%s errors=%s", request.url.path, exc.errors())
        payload = error_response(
            code=ErrorCodes.VALIDATION_ERROR.code,
            message=ErrorCodes.VALIDATION_ERROR.message,
            trace_id=get_trace_id(),
            data={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未捕获异常: path=%s", request.url.path)
        payload = error_response(
            code=ErrorCodes.INTERNAL_ERROR.code,
            message=ErrorCodes.INTERNAL_ERROR.message,
            trace_id=get_trace_id(),
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

