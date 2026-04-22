# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:25
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin


class AskLog(Base, CreatedAtMixin):
    __tablename__ = "ask_log"
    __table_args__ = (
        Index("idx_ask_log_trace_id", "trace_id"),
        Index("idx_ask_log_route", "route"),
        Index("idx_ask_log_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="全链路trace_id")
    question: Mapped[str] = mapped_column(String(2000), nullable=False, comment="用户问题")
    route: Mapped[str] = mapped_column(String(32), nullable=False, comment="路由类型")
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最终回答")
    tools_used_json: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="实际调用工具列表"
    )
    analysis_result_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="分析结果"
    )
    retrieval_result_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="检索结果"
    )
    explanation_result_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="解释结果"
    )
    trace_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True, comment="工具调用链路"
    )
    subject_audit_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_result.id"),
        nullable=True,
        comment="关联的审核结果ID",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="success",
        comment="请求状态，如 success / failed",
    )

    subject_audit_result: Mapped["AuditResult | None"] = relationship(back_populates="ask_logs")
    model_call_logs: Mapped[list["ModelCallLog"]] = relationship(
        back_populates="ask_log",
        cascade="all, delete-orphan",
    )
