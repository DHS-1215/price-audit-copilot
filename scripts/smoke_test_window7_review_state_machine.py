# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/25 17:32
IDE       :PyCharm
作者      :董宏升

7号窗口 smoke test：复核状态机

验证目标：
1. pending 可以 confirm
2. confirmed 不允许 reject / ignore / confirm
3. confirmed 可以 close
4. closed 不允许再执行状态动作
5. closed 仍允许 add_comment

8号窗口调整：
review API 已统一响应外壳：
{
    "success": true,
    "code": "OK",
    "message": "success",
    "trace_id": "...",
    "data": {...}
}
所以 smoke test 需要先 unwrap，再读取 task/items 等业务字段。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import sys
from typing import Any

import requests

BASE_URL = "http://127.0.0.1:8000"
AUDIT_RESULT_ID = 259


def print_title(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def pass_msg(message: str) -> None:
    print(f"[PASS] {message}")


def fail_msg(message: str) -> None:
    print(f"[FAIL] {message}")


def request_raw(method: str, path: str, **kwargs: Any) -> requests.Response:
    return requests.request(
        method=method,
        url=f"{BASE_URL}{path}",
        timeout=30,
        **kwargs,
    )


def unwrap_api_response(payload: dict[str, Any]) -> dict[str, Any]:
    """
    兼容统一响应外壳。

    旧结构：
        {"task": {...}}

    新结构：
        {
            "success": true,
            "code": "OK",
            "message": "success",
            "trace_id": "...",
            "data": {"task": {...}}
        }
    """
    if not isinstance(payload, dict):
        raise TypeError(f"响应不是 dict：{type(payload)}")

    if "success" in payload and "data" in payload:
        if payload.get("success") is not True:
            raise RuntimeError(f"接口返回 success=false：{payload}")

        data = payload.get("data")
        if data is None:
            return {}

        if not isinstance(data, dict):
            raise TypeError(f"统一响应 data 不是 dict：{type(data)}, payload={payload}")

        return data

    return payload


def get_error_message(payload: dict[str, Any]) -> str:
    """
    兼容两种错误响应：
    1. FastAPI 默认错误：{"detail": "..."}
    2. 项目统一错误：{"success": false, "code": "...", "message": "..."}
    """
    if not isinstance(payload, dict):
        return str(payload)

    return str(
        payload.get("detail")
        or payload.get("message")
        or payload.get("error")
        or payload
    )


def request_json_ok(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    response = request_raw(method, path, **kwargs)

    try:
        payload = response.json()
    except Exception:
        payload = {"raw_text": response.text}

    if response.status_code >= 400:
        raise RuntimeError(
            f"{method} {path} failed, "
            f"status={response.status_code}, response={payload}"
        )

    return unwrap_api_response(payload)


def assert_status_code(
        method: str,
        path: str,
        expected_status: int,
        **kwargs: Any,
) -> dict[str, Any]:
    response = request_raw(method, path, **kwargs)

    try:
        payload = response.json()
    except Exception:
        payload = {"raw_text": response.text}

    if response.status_code != expected_status:
        raise AssertionError(
            f"{method} {path} expected {expected_status}, "
            f"got {response.status_code}, response={payload}"
        )

    return payload


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
                    "reviewer": "state_machine_test",
                    "remark": "测试前关闭历史任务",
                },
            )
            continue

        if task_status in {"pending", "processing"}:
            request_raw(
                "POST",
                f"/api/v1/reviews/tasks/{task_id}/ignore",
                json={
                    "reviewer": "state_machine_test",
                    "remark": "测试前忽略历史待处理任务",
                },
            )


def create_task() -> int:
    payload = {
        "audit_result_id": AUDIT_RESULT_ID,
        "task_status": "pending",
        "priority": "high",
        "assigned_to": "状态机测试",
        "created_by": "state_machine_test",
    }

    data = request_json_ok(
        "POST",
        "/api/v1/reviews/tasks",
        json=payload,
    )

    task_id = int(data["task"]["id"])
    assert data["task"]["task_status"] == "pending"

    pass_msg(f"创建 pending 复核任务成功 - task_id={task_id}")
    return task_id


def confirm_from_pending(task_id: int) -> None:
    data = request_json_ok(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/confirm",
        json={
            "reviewer": "状态机测试",
            "remark": "pending -> confirmed",
        },
    )

    assert data["task"]["task_status"] == "confirmed"
    pass_msg("pending -> confirmed 允许")


def confirmed_should_reject_invalid_actions(task_id: int) -> None:
    payload = {
        "reviewer": "状态机测试",
        "remark": "confirmed 状态下不应允许该动作",
    }

    for action in ["confirm", "reject", "ignore"]:
        data = assert_status_code(
            "POST",
            f"/api/v1/reviews/tasks/{task_id}/{action}",
            409,
            json=payload,
        )

        error_message = get_error_message(data)
        assert "不允许" in error_message, data

    pass_msg("confirmed 状态下禁止 confirm / reject / ignore")


def close_from_confirmed(task_id: int) -> None:
    data = request_json_ok(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/close",
        json={
            "reviewer": "状态机测试",
            "remark": "confirmed -> closed",
        },
    )

    assert data["task"]["task_status"] == "closed"
    pass_msg("confirmed -> closed 允许")


def closed_should_reject_state_actions(task_id: int) -> None:
    payload = {
        "reviewer": "状态机测试",
        "remark": "closed 状态下不应允许状态动作",
    }

    for action in ["confirm", "reject", "ignore", "close"]:
        data = assert_status_code(
            "POST",
            f"/api/v1/reviews/tasks/{task_id}/{action}",
            409,
            json=payload,
        )

        error_message = get_error_message(data)
        assert "不允许" in error_message, data

    pass_msg("closed 状态下禁止所有状态动作")


def closed_should_allow_comment(task_id: int) -> None:
    data = request_json_ok(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/comment",
        json={
            "reviewer": "状态机测试",
            "remark": "closed 状态仍允许补充备注",
        },
    )

    assert data["task"]["task_status"] == "closed"
    pass_msg("closed 状态下仍允许 add_comment")


def main() -> int:
    print_title("7号窗口 smoke test：复核状态机")

    try:
        close_existing_tasks_if_needed()

        task_id = create_task()
        confirm_from_pending(task_id)
        confirmed_should_reject_invalid_actions(task_id)
        close_from_confirmed(task_id)
        closed_should_reject_state_actions(task_id)
        closed_should_allow_comment(task_id)

    except Exception as exc:
        fail_msg(str(exc))
        return 1

    print_title("7号窗口状态机验收结果")
    print("PASS: 6")
    print("FAIL: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
