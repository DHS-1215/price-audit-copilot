# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:25
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin


class ModelCallLog(Base, CreatedAtMixin):
    __tablename__ = "model_call_log"
    __table_args__ = (
        Index("idx_model_call_log_ask_log_id", "ask_log_id"),
        Index("idx_model_call_log_trace_id", "trace_id"),
        Index("idx_model_call_log_call_stage", "call_stage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    ask_log_id: Mapped[int] = mapped_column(
        ForeignKey("ask_log.id"),
        nullable=False,
        comment="对应 ask_log.id",
    )
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="trace_id")
    call_stage: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="调用阶段，如 route_classifier / explanation / summary",
    )
    model_vendor: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="模型提供方"
    )
    model_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="模型名称"
    )
    request_payload_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="请求载荷"
    )
    response_payload_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="响应载荷"
    )
    prompt_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="输入tokens"
    )
    completion_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="输出tokens"
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="耗时毫秒"
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="错误信息"
    )

    ask_log: Mapped["AskLog"] = relationship(back_populates="model_call_logs")
