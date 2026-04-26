# -*- coding: utf-8 -*-
from __future__ import annotations

"""
8号窗口 pytest：review API 统一响应契约测试

测试目标：
1. review API 成功响应必须统一使用 ApiResponse 外壳
2. success/code/message/trace_id/data 字段必须存在
3. trace_id 不能为空
4. data 内仍保留原业务字段，比如 task/items/records
5. 不破坏 7号窗口人工复核闭环
"""

from typing import Any

import requests

BASE_URL = "http://127.0.0.1:8000"
AUDIT_RESULT_ID = 259


def request_raw(method: str, path: str, **kwargs: Any) -> requests.Response:
    return requests.request(
        method=method,
        url=f"{BASE_URL}{path}",
        timeout=30,
        **kwargs,
    )


def assert_api_response(payload: dict[str, Any]) -> dict[str, Any]:
    assert isinstance(payload, dict)

    assert payload.get("success") is True
    assert payload.get("code") == "OK"
    assert payload.get("message") == "success"

    assert "trace_id" in payload
    assert isinstance(payload["trace_id"], str)
    assert payload["trace_id"].strip() != ""

    assert "data" in payload
    assert isinstance(payload["data"], dict)

    return payload["data"]


def request_json_ok(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    response = request_raw(method, path, **kwargs)

    try:
        payload = response.json()
    except Exception:
        raise AssertionError(f"响应不是 JSON：status={response.status_code}, text={response.text}")

    assert response.status_code < 400, payload
    return assert_api_response(payload)


def close_existing_tasks_if_needed() -> None:
    data = request_json_ok(
        "GET",
        "/api/v1/reviews/tasks?page=1&page_size=100",
    )

    for item in data.get("items", []):
        if item.get("audit_result_id") != AUDIT_RESULT_ID:
            continue

        task_id = item["id"]
        task_status = item.get("task_status")

        if task_status in {"closed", "ignored"}:
            continue

        if task_status in {"confirmed", "rejected"}:
            request_raw(
                "POST",
                f"/api/v1/reviews/tasks/{task_id}/close",
                json={
                    "reviewer": "pytest_response_contract",
                    "remark": "pytest 前关闭历史任务",
                },
            )
            continue

        if task_status in {"pending", "processing"}:
            request_raw(
                "POST",
                f"/api/v1/reviews/tasks/{task_id}/ignore",
                json={
                    "reviewer": "pytest_response_contract",
                    "remark": "pytest 前忽略历史待处理任务",
                },
            )


def test_create_review_task_uses_unified_response_contract() -> None:
    close_existing_tasks_if_needed()

    payload = {
        "audit_result_id": AUDIT_RESULT_ID,
        "task_status": "pending",
        "priority": "high",
        "assigned_to": "pytest_reviewer",
        "created_by": "pytest",
    }

    data = request_json_ok(
        "POST",
        "/api/v1/reviews/tasks",
        json=payload,
    )

    assert "task" in data
    assert data["task"]["audit_result_id"] == AUDIT_RESULT_ID
    assert data["task"]["task_status"] == "pending"
    assert data["task"]["assigned_to"] == "pytest_reviewer"


def test_list_review_tasks_uses_unified_response_contract() -> None:
    data = request_json_ok(
        "GET",
        "/api/v1/reviews/tasks?page=1&page_size=10",
    )

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


def test_review_records_uses_unified_response_contract() -> None:
    data = request_json_ok(
        "GET",
        "/api/v1/reviews/records?limit=10",
    )

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


def test_review_export_uses_unified_response_contract() -> None:
    data = request_json_ok(
        "GET",
        "/api/v1/reviews/export",
    )

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
