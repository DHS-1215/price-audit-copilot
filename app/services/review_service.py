# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/25 16:11
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.audit_result import AuditResult
from app.models.review_task import ReviewTask
from app.repositories.review_repository import ReviewRepository
from app.schemas.review import (
    ReviewActionRequest,
    ReviewCommentRequest,
    ReviewExportItem,
    ReviewExportResponse,
    ReviewRecordListResponse,
    ReviewRecordRead,
    ReviewTaskCreate,
    ReviewTaskDetailResponse,
    ReviewTaskListItem,
    ReviewTaskListResponse,
    ReviewTaskRead,
)


class ReviewService:
    """
    人工复核业务服务层。

    负责：
    - 创建复核任务
    - 查询复核任务
    - 确认异常
    - 标记误报
    - 添加备注
    - 忽略任务
    - 关闭任务
    - 查询复核历史
    - 导出复核结果

    注意：
    这里不重新判定异常，只基于 audit_result 做人工处理。
    """

    ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
        "pending": {"confirmed", "rejected", "ignored"},
        "processing": {"confirmed", "rejected", "ignored"},
        "confirmed": {"closed"},
        "rejected": {"closed"},
        "ignored": {"closed"},
        "closed": set(),
        "done": set(),
    }

    STATUS_LABELS: dict[str, str] = {
        "pending": "待复核",
        "processing": "处理中",
        "confirmed": "已确认异常",
        "rejected": "已判定误报",
        "ignored": "已忽略",
        "closed": "已关闭",
        "done": "已完成",
    }

    @staticmethod
    def _get_task_or_404(db: Session, task_id: int) -> ReviewTask:
        task = ReviewRepository.get_task(db, task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"复核任务不存在：task_id={task_id}",
            )
        return task

    @staticmethod
    def _get_audit_result_or_404(db: Session, audit_result_id: int) -> AuditResult:
        audit_result = ReviewRepository.get_audit_result(db, audit_result_id)
        if audit_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"审核结果不存在：audit_result_id={audit_result_id}",
            )
        return audit_result

    @staticmethod
    def _build_audit_snapshot(audit_result: AuditResult) -> dict[str, Any]:
        return {
            "audit_result_id": audit_result.id,
            "clean_id": audit_result.clean_id,
            "anomaly_type": audit_result.anomaly_type,
            "is_hit": audit_result.is_hit,
            "hit_rule_code": audit_result.hit_rule_code,
            "hit_rule_version": audit_result.hit_rule_version,
            "rule_definition_id": audit_result.rule_definition_id,
            "reason_text": audit_result.reason_text,
            "result_status": audit_result.result_status,
            "low_price_rule_source": audit_result.low_price_rule_source,
            "explicit_low_price_threshold": (
                str(audit_result.explicit_low_price_threshold)
                if audit_result.explicit_low_price_threshold is not None
                else None
            ),
            "group_avg_price": (
                str(audit_result.group_avg_price)
                if audit_result.group_avg_price is not None
                else None
            ),
            "price_to_group_avg_ratio": (
                str(audit_result.price_to_group_avg_ratio)
                if audit_result.price_to_group_avg_ratio is not None
                else None
            ),
            "input_snapshot_json": audit_result.input_snapshot_json,
            "audited_at": audit_result.audited_at.isoformat()
            if audit_result.audited_at
            else None,
        }

    # 状态流转校验函数
    @staticmethod
    def _ensure_transition_allowed(
            current_status: str,
            target_status: str,
    ) -> None:
        allowed_targets = ReviewService.ALLOWED_STATUS_TRANSITIONS.get(
            current_status,
            set(),
        )

        if target_status not in allowed_targets:
            current_label = ReviewService.STATUS_LABELS.get(current_status, current_status)
            target_label = ReviewService.STATUS_LABELS.get(target_status, target_status)

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "当前复核任务状态不允许执行该动作："
                    f"{current_status}({current_label}) -> "
                    f"{target_status}({target_label})"
                ),
            )

    @staticmethod
    def _build_task_detail(db: Session, task: ReviewTask) -> ReviewTaskDetailResponse:
        audit_result = ReviewService._get_audit_result_or_404(
            db,
            task.audit_result_id,
        )

        records = ReviewRepository.list_records(
            db,
            review_task_id=task.id,
            limit=200,
        )

        return ReviewTaskDetailResponse(
            task=ReviewTaskRead.model_validate(task),
            records=[ReviewRecordRead.model_validate(record) for record in records],
            audit_snapshot=ReviewService._build_audit_snapshot(audit_result),
        )

    @staticmethod
    def create_task(
            db: Session,
            payload: ReviewTaskCreate,
    ) -> ReviewTaskDetailResponse:
        ReviewService._get_audit_result_or_404(db, payload.audit_result_id)

        existing_task = ReviewRepository.get_task_by_audit_result_id(
            db,
            payload.audit_result_id,
        )

        if existing_task and existing_task.task_status not in {"closed", "ignored"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "该审核结果已存在未关闭的复核任务，"
                    f"task_id={existing_task.id}, status={existing_task.task_status}"
                ),
            )

        task = ReviewRepository.create_task(
            db,
            audit_result_id=payload.audit_result_id,
            task_status=payload.task_status,
            priority=payload.priority,
            assigned_to=payload.assigned_to,
            assigned_at=payload.assigned_at,
            due_at=payload.due_at,
            created_by=payload.created_by,
        )

        ReviewRepository.create_record(
            db,
            review_task_id=task.id,
            action_type="add_remark",
            action_result="task_created",
            reviewer=payload.created_by,
            remark="创建人工复核任务",
            evidence_snapshot_json={
                "audit_result_id": payload.audit_result_id,
                "source": "review_task_create",
            },
        )

        db.commit()
        db.refresh(task)

        return ReviewService._build_task_detail(db, task)

    @staticmethod
    def list_tasks(
            db: Session,
            *,
            task_status: str | None = None,
            priority: str | None = None,
            assigned_to: str | None = None,
            page: int = 1,
            page_size: int = 20,
    ) -> ReviewTaskListResponse:
        total = ReviewRepository.count_tasks(
            db,
            task_status=task_status,
            priority=priority,
            assigned_to=assigned_to,
        )

        tasks = ReviewRepository.list_tasks(
            db,
            task_status=task_status,
            priority=priority,
            assigned_to=assigned_to,
            page=page,
            page_size=page_size,
        )

        return ReviewTaskListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[ReviewTaskListItem.model_validate(task) for task in tasks],
        )

    @staticmethod
    def get_task_detail(
            db: Session,
            task_id: int,
    ) -> ReviewTaskDetailResponse:
        task = ReviewService._get_task_or_404(db, task_id)
        return ReviewService._build_task_detail(db, task)

    @staticmethod
    def confirm_task(
            db: Session,
            task_id: int,
            payload: ReviewActionRequest,
    ) -> ReviewTaskDetailResponse:
        task = ReviewService._get_task_or_404(db, task_id)
        ReviewService._ensure_transition_allowed(task.task_status, "confirmed")

        audit_result = ReviewService._get_audit_result_or_404(db, task.audit_result_id)

        snapshot = payload.evidence_snapshot_json or ReviewService._build_audit_snapshot(audit_result)

        ReviewRepository.update_task_status(
            db,
            task,
            task_status="confirmed",
        )
        ReviewRepository.update_audit_result_status(
            db,
            audit_result,
            result_status="confirmed_abnormal",
        )
        ReviewRepository.create_record(
            db,
            review_task_id=task.id,
            action_type="confirm_abnormal",
            action_result="confirmed",
            reviewer=payload.reviewer,
            remark=payload.remark,
            evidence_snapshot_json=snapshot,
        )

        db.commit()
        db.refresh(task)

        return ReviewService._build_task_detail(db, task)

    @staticmethod
    def reject_task(
            db: Session,
            task_id: int,
            payload: ReviewActionRequest,
    ) -> ReviewTaskDetailResponse:
        task = ReviewService._get_task_or_404(db, task_id)
        ReviewService._ensure_transition_allowed(task.task_status, "rejected")

        audit_result = ReviewService._get_audit_result_or_404(db, task.audit_result_id)

        snapshot = payload.evidence_snapshot_json or ReviewService._build_audit_snapshot(audit_result)

        ReviewRepository.update_task_status(
            db,
            task,
            task_status="rejected",
        )
        ReviewRepository.update_audit_result_status(
            db,
            audit_result,
            result_status="false_positive",
        )
        ReviewRepository.create_record(
            db,
            review_task_id=task.id,
            action_type="mark_false_positive",
            action_result="rejected",
            reviewer=payload.reviewer,
            remark=payload.remark,
            evidence_snapshot_json=snapshot,
        )

        db.commit()
        db.refresh(task)

        return ReviewService._build_task_detail(db, task)

    @staticmethod
    def add_comment(
            db: Session,
            task_id: int,
            payload: ReviewCommentRequest,
    ) -> ReviewTaskDetailResponse:
        task = ReviewService._get_task_or_404(db, task_id)

        ReviewRepository.create_record(
            db,
            review_task_id=task.id,
            action_type="add_remark",
            action_result="comment_added",
            reviewer=payload.reviewer,
            remark=payload.remark,
            evidence_snapshot_json=payload.evidence_snapshot_json,
        )

        db.commit()
        db.refresh(task)

        return ReviewService._build_task_detail(db, task)

    @staticmethod
    def ignore_task(
            db: Session,
            task_id: int,
            payload: ReviewActionRequest,
    ) -> ReviewTaskDetailResponse:
        task = ReviewService._get_task_or_404(db, task_id)
        ReviewService._ensure_transition_allowed(task.task_status, "ignored")

        audit_result = ReviewService._get_audit_result_or_404(db, task.audit_result_id)

        snapshot = payload.evidence_snapshot_json or ReviewService._build_audit_snapshot(audit_result)

        ReviewRepository.update_task_status(
            db,
            task,
            task_status="ignored",
        )
        ReviewRepository.update_audit_result_status(
            db,
            audit_result,
            result_status="ignored",
        )
        ReviewRepository.create_record(
            db,
            review_task_id=task.id,
            action_type="ignore_task",
            action_result="ignored",
            reviewer=payload.reviewer,
            remark=payload.remark,
            evidence_snapshot_json=snapshot,
        )

        db.commit()
        db.refresh(task)

        return ReviewService._build_task_detail(db, task)

    @staticmethod
    def close_task(
            db: Session,
            task_id: int,
            payload: ReviewActionRequest,
    ) -> ReviewTaskDetailResponse:
        task = ReviewService._get_task_or_404(db, task_id)
        ReviewService._ensure_transition_allowed(task.task_status, "closed")

        ReviewRepository.update_task_status(
            db,
            task,
            task_status="closed",
        )
        ReviewRepository.create_record(
            db,
            review_task_id=task.id,
            action_type="close_task",
            action_result="closed",
            reviewer=payload.reviewer,
            remark=payload.remark,
            evidence_snapshot_json=payload.evidence_snapshot_json,
        )

        db.commit()
        db.refresh(task)

        return ReviewService._build_task_detail(db, task)

    @staticmethod
    def list_records(
            db: Session,
            *,
            review_task_id: int | None = None,
            limit: int = 100,
    ) -> ReviewRecordListResponse:
        records = ReviewRepository.list_records(
            db,
            review_task_id=review_task_id,
            limit=limit,
        )

        return ReviewRecordListResponse(
            total=len(records),
            items=[ReviewRecordRead.model_validate(record) for record in records],
        )

    @staticmethod
    def export_tasks(
            db: Session,
            *,
            task_status: str | None = None,
            assigned_to: str | None = None,
    ) -> ReviewExportResponse:
        tasks = ReviewRepository.list_tasks(
            db,
            task_status=task_status,
            priority=None,
            assigned_to=assigned_to,
            page=1,
            page_size=1000,
        )

        items: list[ReviewExportItem] = []

        for task in tasks:
            records = ReviewRepository.list_records(
                db,
                review_task_id=task.id,
                limit=1,
            )
            latest = records[0] if records else None

            items.append(
                ReviewExportItem(
                    task_id=task.id,
                    audit_result_id=task.audit_result_id,
                    task_status=task.task_status,
                    priority=task.priority,
                    assigned_to=task.assigned_to,
                    created_by=task.created_by,
                    latest_action_type=latest.action_type if latest else None,
                    latest_action_result=latest.action_result if latest else None,
                    latest_reviewer=latest.reviewer if latest else None,
                    latest_remark=latest.remark if latest else None,
                    latest_action_at=latest.created_at if latest else None,
                )
            )

        return ReviewExportResponse(
            total=len(items),
            items=items,
        )
