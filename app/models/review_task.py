# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:25
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ReviewTask(Base, TimestampMixin):
    """
    人工复核任务表。

    一条 review_task 对应一条 audit_result。
    它表示“这条异常结果是否需要业务人员处理，以及当前处理到什么状态”。
    """

    __tablename__ = "review_task"
    __table_args__ = (
        Index("idx_review_task_audit_result_id", "audit_result_id"),
        Index("idx_review_task_status_assigned", "task_status", "assigned_to"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键",
    )

    audit_result_id: Mapped[int] = mapped_column(
        ForeignKey("audit_result.id"),
        nullable=False,
        comment="对应 audit_result.id",
    )

    task_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        comment="任务状态：pending / processing / confirmed / rejected / ignored / closed",
    )

    priority: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="优先级：low / medium / high",
    )

    assigned_to: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="分配对象",
    )

    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="分配时间",
    )

    due_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="截止时间",
    )

    created_by: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="创建人",
    )

    audit_result: Mapped["AuditResult"] = relationship(
        back_populates="review_tasks",
    )

    review_records: Mapped[list["ReviewRecord"]] = relationship(
        back_populates="review_task",
        cascade="all, delete-orphan",
    )