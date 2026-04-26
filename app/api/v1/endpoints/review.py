# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 12:10
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, success_response
from app.core.trace import get_trace_id
from app.db.session import get_db
from app.schemas.review import (
    ReviewActionRequest,
    ReviewCommentRequest,
    ReviewTaskCreate,
    ReviewTaskPriority,
    ReviewTaskStatus,
)
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post(
    "/tasks",
    response_model=ApiResponse,
    summary="创建人工复核任务",
)
def create_review_task(
        payload: ReviewTaskCreate,
        db: Session = Depends(get_db),
) -> ApiResponse:
    result = ReviewService.create_task(db, payload)
    return success_response(data=result, trace_id=get_trace_id())


@router.get(
    "/tasks",
    response_model=ApiResponse,
    summary="查询人工复核任务列表",
)
def list_review_tasks(
        task_status: ReviewTaskStatus | None = Query(default=None, description="任务状态"),
        priority: ReviewTaskPriority | None = Query(default=None, description="优先级"),
        assigned_to: str | None = Query(default=None, description="分配对象"),
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
        db: Session = Depends(get_db),
) -> ApiResponse:
    result = ReviewService.list_tasks(
        db,
        task_status=task_status,
        priority=priority,
        assigned_to=assigned_to,
        page=page,
        page_size=page_size,
    )
    return success_response(data=result, trace_id=get_trace_id())


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse,
    summary="查询人工复核任务详情",
)
def get_review_task_detail(
        task_id: int,
        db: Session = Depends(get_db),
) -> ApiResponse:
    result = ReviewService.get_task_detail(db, task_id)
    return success_response(data=result, trace_id=get_trace_id())


@router.post(
    "/tasks/{task_id}/confirm",
    response_model=ApiResponse,
    summary="确认异常",
)
def confirm_review_task(
        task_id: int,
        payload: ReviewActionRequest,
        db: Session = Depends(get_db),
) -> ApiResponse:
    result = ReviewService.confirm_task(db, task_id, payload)
    return success_response(data=result, trace_id=get_trace_id())


@router.post(
    "/tasks/{task_id}/reject",
    response_model=ApiResponse,
    summary="标记为误报",
)
def reject_review_task(
        task_id: int,
        payload: ReviewActionRequest,
        db: Session = Depends(get_db),
) -> ApiResponse:
    result = ReviewService.reject_task(db, task_id, payload)
    return success_response(data=result, trace_id=get_trace_id())


@router.post(
    "/tasks/{task_id}/comment",
    response_model=ApiResponse,
    summary="添加复核备注",
)
def comment_review_task(
        task_id: int,
        payload: ReviewCommentRequest,
        db: Session = Depends(get_db),
) -> ApiResponse:
    result = ReviewService.add_comment(db, task_id, payload)
    return success_response(data=result, trace_id=get_trace_id())


@router.post(
    "/tasks/{task_id}/ignore",
    response_model=ApiResponse,
    summary="忽略复核任务",
)
def ignore_review_task(
        task_id: int,
        payload: ReviewActionRequest,
        db: Session = Depends(get_db),
) -> ApiResponse:
    result = ReviewService.ignore_task(db, task_id, payload)
    return success_response(data=result, trace_id=get_trace_id())


@router.post(
    "/tasks/{task_id}/close",
    response_model=ApiResponse,
    summary="关闭复核任务",
)
def close_review_task(
        task_id: int,
        payload: ReviewActionRequest,
        db: Session = Depends(get_db),
) -> ApiResponse:
    result = ReviewService.close_task(db, task_id, payload)
    return success_response(data=result, trace_id=get_trace_id())


@router.get(
    "/records",
    response_model=ApiResponse,
    summary="查询人工复核记录",
)
def list_review_records(
        review_task_id: int | None = Query(default=None, description="复核任务ID"),
        limit: int = Query(default=100, ge=1, le=1000, description="返回数量"),
        db: Session = Depends(get_db),
) -> ApiResponse:
    result = ReviewService.list_records(
        db,
        review_task_id=review_task_id,
        limit=limit,
    )
    return success_response(data=result, trace_id=get_trace_id())


@router.get(
    "/export",
    response_model=ApiResponse,
    summary="导出人工复核结果",
)
def export_review_tasks(
        task_status: ReviewTaskStatus | None = Query(default=None, description="任务状态"),
        assigned_to: str | None = Query(default=None, description="分配对象"),
        db: Session = Depends(get_db),
) -> ApiResponse:
    result = ReviewService.export_tasks(
        db,
        task_status=task_status,
        assigned_to=assigned_to,
    )
    return success_response(data=result, trace_id=get_trace_id())