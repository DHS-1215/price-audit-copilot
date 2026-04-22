# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 13:24
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


from app.core.config import get_settings
from app.core.context import get_request_method, get_request_path, get_trace_id


class RequestContextFilter(logging.Filter):
    """
    给日志记录补充请求上下文字段。

    这样 formatter 里就能统一使用 %(trace_id)s / %(request_method)s / %(request_path)s。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id() or "-"
        record.request_method = get_request_method() or "-"
        record.request_path = get_request_path() or "-"
        return True


def _build_formatter() -> logging.Formatter:
    """
    统一日志格式。

    日志字段建议先围绕 3 号窗口要求来：
    时间、级别、模块名、trace_id、请求信息、消息文本。
    """
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
    """
    初始化全局日志。

    约定：
    1. 只在应用启动时调用一次
    2. 根 logger 统一挂载 handler
    3. 避免重复初始化导致日志重复打印
    """
    settings = get_settings()

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    root_logger.addHandler(_build_stream_handler())
    root_logger.addHandler(_build_file_handler(settings.log_file_path))


def get_logger(name: str) -> logging.Logger:
    """
    获取模块 logger。
    用法：
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)