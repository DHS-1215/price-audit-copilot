# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 14:18
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from contextvars import ContextVar

trace_id_ctx_var: ContextVar[str] = ContextVar("trace_id", default="")
request_path_ctx_var: ContextVar[str] = ContextVar("request_path", default="")
request_method_ctx_var: ContextVar[str] = ContextVar("request_method", default="")


def set_trace_id(trace_id: str) -> None:
    trace_id_ctx_var.set(trace_id)


def get_trace_id() -> str:
    return trace_id_ctx_var.get()


def set_request_meta(method: str, path: str) -> None:
    request_method_ctx_var.set(method)
    request_path_ctx_var.set(path)


def get_request_method() -> str:
    return request_method_ctx_var.get()


def get_request_path() -> str:
    return request_path_ctx_var.get()


def clear_request_context() -> None:
    """
    请求结束后可主动清理上下文。
    虽然 ContextVar 通常随协程上下文结束而结束，
    但显式清理更稳，也更利于排查问题。
    """
    trace_id_ctx_var.set("")
    request_method_ctx_var.set("")
    request_path_ctx_var.set("")
