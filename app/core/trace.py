# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 14:19
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid

from fastapi import Request

from app.core.config import get_settings
from app.core.context import get_trace_id as get_current_trace_id
from app.core.context import set_trace_id


def generate_trace_id() -> str:
    """
    生成 trace_id。

    这里用 uuid4 的 hex 前 32 位，简单稳定，够用。
    后面如果要换成更短格式，也只需要改这一处。
    """
    return uuid.uuid4().hex


def resolve_trace_id(request: Request) -> str:
    """
    解析本次请求的 trace_id。

    规则：
    1. 先读请求头中的 X-Trace-Id（或配置中定义的 header 名）
    2. 若没有，则服务端生成
    3. 写入 request.state 和 ContextVar，后续全链路复用
    """
    settings = get_settings()
    header_name = settings.trace_header_name

    incoming_trace_id = request.headers.get(header_name, "").strip()
    trace_id = incoming_trace_id or generate_trace_id()

    request.state.trace_id = trace_id
    set_trace_id(trace_id)
    return trace_id


def get_trace_id() -> str:
    """
    获取当前上下文中的 trace_id。
    """
    return get_current_trace_id()
