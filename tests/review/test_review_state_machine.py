# -*- coding: utf-8 -*-
from __future__ import annotations

"""
8号窗口 pytest：人工复核状态机测试

测试目标：
1. pending 可以 confirm
2. confirmed 不允许 confirm / reject / ignore
3. confirmed 可以 close
4. closed 不允许 confirm / reject / ignore / close
5. closed 仍允许 add_comment

说明：
这里是集成测试风格 pytest，依赖本地 FastAPI 服务与测试数据库已启动。
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


def unwrap_api_response(payload: dict[str, Any]) -> dict[str, Any]:
    assert isinstance(payload, dict)

    if "success" in payload and "data" in payload:
        assert payload["success"] is True, payload
        assert payload["code"] == "OK", payload
        assert payload["trace_id"].strip() != "", payload

        data = payload["data"]
        assert isinstance(data, dict), payload
        return data

    return payload


def request_json_ok(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    response = request_raw(method, path, **kwargs)
    payload = response.json()

    assert response.status_code < 400, payload
    return unwrap_api_response(payload)


def request_json_with_status(
        method: str,
        path: str,
        expected_status: int,
        **kwargs: Any,
) -> dict[str, Any]:
    response = request_raw(method, path, **kwargs)
    payload = response.json()

    assert response.status_code == expected_status, payload
    return payload


def get_error_message(payload: dict[str, Any]) -> str:
    return str(
        payload.get("detail")
        or payload.get("message")
        or payload.get("error")
        or payload
    )


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
                    "reviewer": "pytest_state_machine",
                    "remark": "pytest 前关闭历史任务",
                },
            )
            continue

        if task_status in {"pending", "processing"}:
            request_raw(
                "POST",
                f"/api/v1/reviews/tasks/{task_id}/ignore",
                json={
                    "reviewer": "pytest_state_machine",
                    "remark": "pytest 前忽略历史待处理任务",
                },
            )


def create_pending_task() -> int:
    close_existing_tasks_if_needed()

    payload = {
        "audit_result_id": AUDIT_RESULT_ID,
        "task_status": "pending",
        "priority": "high",
        "assigned_to": "pytest_state_machine",
        "created_by": "pytest",
    }

    data = request_json_ok(
        "POST",
        "/api/v1/reviews/tasks",
        json=payload,
    )

    task = data["task"]
    assert task["task_status"] == "pending"

    return int(task["id"])


def test_review_state_machine_confirmed_and_closed_flow() -> None:
    task_id = create_pending_task()

    confirm_data = request_json_ok(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/confirm",
        json={
            "reviewer": "pytest_state_machine",
            "remark": "pending -> confirmed",
        },
    )

    assert confirm_data["task"]["task_status"] == "confirmed"

    for action in ["confirm", "reject", "ignore"]:
        error_payload = request_json_with_status(
            "POST",
            f"/api/v1/reviews/tasks/{task_id}/{action}",
            409,
            json={
                "reviewer": "pytest_state_machine",
                "remark": "confirmed 状态下不允许该动作",
            },
        )

        assert "不允许" in get_error_message(error_payload)

    close_data = request_json_ok(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/close",
        json={
            "reviewer": "pytest_state_machine",
            "remark": "confirmed -> closed",
        },
    )

    assert close_data["task"]["task_status"] == "closed"

    for action in ["confirm", "reject", "ignore", "close"]:
        error_payload = request_json_with_status(
            "POST",
            f"/api/v1/reviews/tasks/{task_id}/{action}",
            409,
            json={
                "reviewer": "pytest_state_machine",
                "remark": "closed 状态下不允许状态动作",
            },
        )

        assert "不允许" in get_error_message(error_payload)

    comment_data = request_json_ok(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/comment",
        json={
            "reviewer": "pytest_state_machine",
            "remark": "closed 状态仍允许补充备注",
        },
    )

    assert comment_data["task"]["task_status"] == "closed"
