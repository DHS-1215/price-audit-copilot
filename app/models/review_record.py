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


class ReviewRecord(Base, CreatedAtMixin):
    """
    人工复核动作记录表。

    一条 review_task 可以有多条 review_record。
    例如：添加备注、确认异常、判定误报、忽略任务。
    """

    __tablename__ = "review_record"
    __table_args__ = (
        Index("idx_review_record_task_id", "review_task_id"),
        Index("idx_review_record_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键",
    )

    review_task_id: Mapped[int] = mapped_column(
        ForeignKey("review_task.id"),
        nullable=False,
        comment="对应 review_task.id",
    )

    action_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="动作类型：confirm_abnormal / mark_false_positive / add_remark / ignore_task / close_task",
    )

    action_result: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="动作结果",
    )

    reviewer: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="复核人",
    )

    remark: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="备注",
    )

    evidence_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="操作时的依据快照",
    )

    review_task: Mapped["ReviewTask"] = relationship(
        back_populates="review_records",
    )
