# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 13:25
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ErrorCode:
    code: str
    message: str


class ErrorCodes:
    OK = ErrorCode("OK", "success")

    BAD_REQUEST = ErrorCode("BAD_REQUEST", "请求参数有误")
    VALIDATION_ERROR = ErrorCode("VALIDATION_ERROR", "请求校验失败")
    NOT_FOUND = ErrorCode("NOT_FOUND", "资源不存在")
    CONFLICT = ErrorCode("CONFLICT", "资源冲突")

    DATABASE_ERROR = ErrorCode("DATABASE_ERROR", "数据库操作失败")
    MODEL_CALL_ERROR = ErrorCode("MODEL_CALL_ERROR", "模型调用失败")
    RETRIEVAL_ERROR = ErrorCode("RETRIEVAL_ERROR", "检索失败")
    RULE_ENGINE_ERROR = ErrorCode("RULE_ENGINE_ERROR", "规则引擎执行失败")
    REVIEW_ACTION_ERROR = ErrorCode("REVIEW_ACTION_ERROR", "复核动作执行失败")

    INTERNAL_ERROR = ErrorCode("INTERNAL_ERROR", "服务器内部错误")


class AppException(Exception):
    """
    项目统一基础异常。
    """

    def __init__(
        self,
        error_code: ErrorCode,
        detail: str | None = None,
        status_code: int = 500,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.error_code = error_code
        self.detail = detail or error_code.message
        self.status_code = status_code
        self.extra = extra or {}
        super().__init__(self.detail)


class BizException(AppException):
    """
    业务异常。
    """
    pass


class ExternalServiceException(AppException):
    """
    外部依赖异常，比如模型、向量库、第三方接口等。
    """
    pass