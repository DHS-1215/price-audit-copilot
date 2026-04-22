# app/core/logger.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import get_settings
from app.core.context import get_request_method, get_request_path, get_trace_id

_LOGGING_INITIALIZED = False


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id() or "-"
        record.request_method = get_request_method() or "-"
        record.request_path = get_request_path() or "-"
        return True


def _build_formatter() -> logging.Formatter:
    log_format = (
        "%(asctime)s | %(levelname)s | %(name)s | "
        "trace_id=%(trace_id)s | %(request_method)s %(request_path)s | "
        "%(message)s"
    )
    return logging.Formatter(log_format)


def _build_stream_handler() -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setFormatter(_build_formatter())
    handler.addFilter(RequestContextFilter())
    return handler


def _build_file_handler(log_file_path: Path) -> logging.Handler:
    handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(_build_formatter())
    handler.addFilter(RequestContextFilter())
    return handler


def setup_logging() -> None:
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return

    settings = get_settings()

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # 只清自己加的旧 handler，避免重复打印
    root_logger.handlers.clear()

    root_logger.addHandler(_build_stream_handler())
    root_logger.addHandler(_build_file_handler(settings.log_file_path))

    _LOGGING_INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
