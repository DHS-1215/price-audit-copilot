# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/25 16:11
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.audit_result import AuditResult
from app.models.review_record import ReviewRecord
from app.models.review_task import ReviewTask


class ReviewRepository:
    """
    人工复核仓储层。

    只负责数据库读写，不写业务判断。
    业务状态流转放在 ReviewService。
    """

    @staticmethod
    def get_audit_result(db: Session, audit_result_id: int) -> AuditResult | None:
        stmt = select(AuditResult).where(AuditResult.id == audit_result_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_task(db: Session, task_id: int) -> ReviewTask | None:
        stmt = (
            select(ReviewTask)
            .options(selectinload(ReviewTask.review_records))
            .where(ReviewTask.id == task_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_task_by_audit_result_id(
            db: Session,
            audit_result_id: int,
    ) -> ReviewTask | None:
        stmt = (
            select(ReviewTask)
            .where(ReviewTask.audit_result_id == audit_result_id)
            .order_by(desc(ReviewTask.created_at))
        )
        return db.execute(stmt).scalars().first()

    @staticmethod
    def create_task(
            db: Session,
            *,
            audit_result_id: int,
            task_status: str = "pending",
            priority: str | None = None,
            assigned_to: str | None = None,
            assigned_at=None,
            due_at=None,
            created_by: str | None = None,
    ) -> ReviewTask:
        task = ReviewTask(
            audit_result_id=audit_result_id,
            task_status=task_status,
            priority=priority,
            assigned_to=assigned_to,
            assigned_at=assigned_at,
            due_at=due_at,
            created_by=created_by,
        )
        db.add(task)
        db.flush()
        db.refresh(task)
        return task

    @staticmethod
    def list_tasks(
            db: Session,
            *,
            task_status: str | None = None,
            priority: str | None = None,
            assigned_to: str | None = None,
            page: int = 1,
            page_size: int = 20,
    ) -> list[ReviewTask]:
        stmt = select(ReviewTask)

        if task_status:
            stmt = stmt.where(ReviewTask.task_status == task_status)
        if priority:
            stmt = stmt.where(ReviewTask.priority == priority)
        if assigned_to:
            stmt = stmt.where(ReviewTask.assigned_to == assigned_to)

        stmt = (
            stmt.order_by(desc(ReviewTask.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def count_tasks(
            db: Session,
            *,
            task_status: str | None = None,
            priority: str | None = None,
            assigned_to: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(ReviewTask)

        if task_status:
            stmt = stmt.where(ReviewTask.task_status == task_status)
        if priority:
            stmt = stmt.where(ReviewTask.priority == priority)
        if assigned_to:
            stmt = stmt.where(ReviewTask.assigned_to == assigned_to)

        return int(db.execute(stmt).scalar_one())

    @staticmethod
    def update_task_status(
            db: Session,
            task: ReviewTask,
            *,
            task_status: str,
    ) -> ReviewTask:
        task.task_status = task_status
        db.add(task)
        db.flush()
        db.refresh(task)
        return task

    @staticmethod
    def create_record(
            db: Session,
            *,
            review_task_id: int,
            action_type: str,
            action_result: str | None = None,
            reviewer: str | None = None,
            remark: str | None = None,
            evidence_snapshot_json: dict[str, Any] | None = None,
    ) -> ReviewRecord:
        record = ReviewRecord(
            review_task_id=review_task_id,
            action_type=action_type,
            action_result=action_result,
            reviewer=reviewer,
            remark=remark,
            evidence_snapshot_json=evidence_snapshot_json,
        )
        db.add(record)
        db.flush()
        db.refresh(record)
        return record

    @staticmethod
    def list_records(
            db: Session,
            *,
            review_task_id: int | None = None,
            limit: int = 100,
    ) -> list[ReviewRecord]:
        stmt = select(ReviewRecord)

        if review_task_id is not None:
            stmt = stmt.where(ReviewRecord.review_task_id == review_task_id)

        stmt = stmt.order_by(desc(ReviewRecord.created_at)).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_audit_result_status(
            db: Session,
            audit_result: AuditResult,
            *,
            result_status: str,
    ) -> AuditResult:
        audit_result.result_status = result_status
        db.add(audit_result)
        db.flush()
        db.refresh(audit_result)
        return audit_result
