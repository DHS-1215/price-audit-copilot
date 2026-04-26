# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 16:26
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ReviewTaskStatus = Literal[
    "pending",
    "processing",
    "confirmed",
    "rejected",
    "ignored",
    "closed",
    "done",
]

ReviewTaskPriority = Literal[
    "low",
    "medium",
    "high",
]

ReviewActionType = Literal[
    "confirm_abnormal",
    "mark_false_positive",
    "add_remark",
    "reassign",
    "ignore_task",
    "close_task",
]


class ReviewTaskBase(BaseModel):
    audit_result_id: int = Field(..., description="对应 audit_result.id")
    task_status: ReviewTaskStatus = Field(default="pending", description="任务状态")
    priority: ReviewTaskPriority | None = Field(default=None, description="优先级")
    assigned_to: str | None = Field(default=None, description="分配对象")
    assigned_at: datetime | None = Field(default=None, description="分配时间")
    due_at: datetime | None = Field(default=None, description="截止时间")
    created_by: str | None = Field(default=None, description="创建人")


class ReviewTaskCreate(ReviewTaskBase):
    pass


class ReviewTaskUpdate(BaseModel):
    task_status: ReviewTaskStatus | None = Field(default=None, description="任务状态")
    priority: ReviewTaskPriority | None = Field(default=None, description="优先级")
    assigned_to: str | None = Field(default=None, description="分配对象")
    assigned_at: datetime | None = Field(default=None, description="分配时间")
    due_at: datetime | None = Field(default=None, description="截止时间")


class ReviewTaskRead(ReviewTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ReviewTaskListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    audit_result_id: int = Field(..., description="审核结果ID")
    task_status: ReviewTaskStatus = Field(..., description="任务状态")
    priority: ReviewTaskPriority | None = Field(default=None, description="优先级")
    assigned_to: str | None = Field(default=None, description="分配对象")
    due_at: datetime | None = Field(default=None, description="截止时间")
    created_by: str | None = Field(default=None, description="创建人")
    created_at: datetime = Field(..., description="创建时间")


class ReviewRecordBase(BaseModel):
    review_task_id: int = Field(..., description="对应 review_task.id")
    action_type: ReviewActionType = Field(..., description="动作类型")
    action_result: str | None = Field(default=None, description="动作结果")
    reviewer: str | None = Field(default=None, description="复核人")
    remark: str | None = Field(default=None, description="备注")
    evidence_snapshot_json: dict[str, Any] | None = Field(
        default=None,
        description="操作时的依据快照",
    )


class ReviewRecordCreate(ReviewRecordBase):
    pass


class ReviewRecordRead(ReviewRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")


class ReviewTaskQuery(BaseModel):
    task_status: ReviewTaskStatus | None = Field(default=None, description="按任务状态筛选")
    priority: ReviewTaskPriority | None = Field(default=None, description="按优先级筛选")
    assigned_to: str | None = Field(default=None, description="按分配对象筛选")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class ReviewTaskListResponse(BaseModel):
    total: int = Field(..., description="总数")
    page: int = Field(..., description="页码")
    page_size: int = Field(..., description="每页数量")
    items: list[ReviewTaskListItem] = Field(default_factory=list, description="任务列表")


class ReviewActionRequest(BaseModel):
    reviewer: str | None = Field(default=None, description="复核人")
    remark: str | None = Field(default=None, description="备注")
    evidence_snapshot_json: dict[str, Any] | None = Field(
        default=None,
        description="前端或解释链传入的依据快照",
    )


class ReviewCommentRequest(BaseModel):
    reviewer: str | None = Field(default=None, description="复核人")
    remark: str = Field(..., min_length=1, description="备注内容")
    evidence_snapshot_json: dict[str, Any] | None = Field(
        default=None,
        description="前端或解释链传入的依据快照",
    )


class ReviewTaskDetailResponse(BaseModel):
    task: ReviewTaskRead = Field(..., description="复核任务")
    records: list[ReviewRecordRead] = Field(default_factory=list, description="复核记录")
    audit_snapshot: dict[str, Any] = Field(default_factory=dict, description="审核结果快照")


class ReviewRecordListResponse(BaseModel):
    total: int = Field(..., description="总数")
    items: list[ReviewRecordRead] = Field(default_factory=list, description="复核记录列表")


class ReviewExportItem(BaseModel):
    task_id: int
    audit_result_id: int
    task_status: str
    priority: str | None = None
    assigned_to: str | None = None
    created_by: str | None = None
    latest_action_type: str | None = None
    latest_action_result: str | None = None
    latest_reviewer: str | None = None
    latest_remark: str | None = None
    latest_action_at: datetime | None = None


class ReviewExportResponse(BaseModel):
    total: int
    items: list[ReviewExportItem] = Field(default_factory=list)