# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/25 16:24
IDE       :PyCharm
作者      :董宏升

7号窗口 smoke test：人工复核闭环

验证目标：
1. 可以创建复核任务
2. 可以查询任务列表
3. 可以查询任务详情
4. 可以添加备注
5. 可以确认异常
6. 可以查询复核记录
7. 可以导出复核结果

注意：
本脚本默认依赖 4/5/6 号窗口已经生成的 SPEC_RISK 正向样本：
audit_result_id = 259

8号窗口调整：
review API 已统一响应外壳：
{
    "success": true,
    "code": "OK",
    "message": "success",
    "trace_id": "...",
    "data": {...}
}
所以 smoke test 需要先 unwrap，再读取 task/items/records 等业务字段。
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


def request_json(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
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


def close_existing_tasks_if_needed() -> None:
    """
    为了让本 smoke test 每次都能创建新的 pending 任务，
    先把同一个 audit_result_id 下未完成的任务处理掉。

    confirmed / rejected -> close
    pending / processing -> ignore
    closed / ignored -> 保持不动
    """
    data = request_json(
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
                    "reviewer": "window7_flow_test",
                    "remark": "flow 测试前关闭历史任务",
                },
            )
            continue

        if task_status in {"pending", "processing"}:
            request_raw(
                "POST",
                f"/api/v1/reviews/tasks/{task_id}/ignore",
                json={
                    "reviewer": "window7_flow_test",
                    "remark": "flow 测试前忽略历史待处理任务",
                },
            )


def create_review_task() -> int:
    payload = {
        "audit_result_id": AUDIT_RESULT_ID,
        "task_status": "pending",
        "priority": "high",
        "assigned_to": "window7_reviewer",
        "created_by": "smoke_test",
    }

    data = request_json(
        "POST",
        "/api/v1/reviews/tasks",
        json=payload,
    )

    task_id = int(data["task"]["id"])
    assert data["task"]["task_status"] == "pending"

    pass_msg(f"创建复核任务成功 - task_id={task_id}")
    return task_id


def test_list_tasks() -> None:
    data = request_json(
        "GET",
        "/api/v1/reviews/tasks?page=1&page_size=10",
    )

    assert "items" in data
    assert data["total"] >= 1

    pass_msg(f"查询复核任务列表成功 - total={data['total']}")


def test_get_task_detail(task_id: int) -> None:
    data = request_json(
        "GET",
        f"/api/v1/reviews/tasks/{task_id}",
    )

    assert data["task"]["id"] == task_id
    assert data["task"]["audit_result_id"] == AUDIT_RESULT_ID
    assert "records" in data
    assert "audit_snapshot" in data

    pass_msg(
        "查询复核任务详情成功 - "
        f"task_status={data['task']['task_status']}, "
        f"records={len(data['records'])}"
    )


def test_add_comment(task_id: int) -> None:
    payload = {
        "reviewer": "window7_reviewer",
        "remark": "window7 smoke test comment",
    }

    data = request_json(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/comment",
        json=payload,
    )

    assert data["task"]["id"] == task_id
    assert len(data["records"]) >= 1

    action_types = {record["action_type"] for record in data["records"]}
    assert "add_remark" in action_types

    pass_msg("添加复核备注成功")


def test_confirm_task(task_id: int) -> None:
    payload = {
        "reviewer": "window7_reviewer",
        "remark": "window7 smoke test confirm abnormal",
    }

    data = request_json(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/confirm",
        json=payload,
    )

    assert data["task"]["id"] == task_id
    assert data["task"]["task_status"] == "confirmed"

    pass_msg("确认异常成功 - task_status=confirmed")


def test_list_records(task_id: int) -> None:
    data = request_json(
        "GET",
        f"/api/v1/reviews/records?review_task_id={task_id}",
    )

    assert "items" in data
    assert data["total"] >= 1

    action_types = {item["action_type"] for item in data["items"]}

    assert "confirm_abnormal" in action_types

    pass_msg(
        "查询复核记录成功 - "
        f"total={data['total']}, action_types={sorted(action_types)}"
    )


def test_export_tasks(task_id: int) -> None:
    data = request_json(
        "GET",
        "/api/v1/reviews/export",
    )

    assert "items" in data
    assert data["total"] >= 1

    task_ids = {item["task_id"] for item in data["items"]}
    assert task_id in task_ids

    pass_msg(f"导出复核结果成功 - total={data['total']}")


def main() -> int:
    print_title("7号窗口 smoke test：人工复核闭环")

    try:
        close_existing_tasks_if_needed()

        task_id = create_review_task()
        test_list_tasks()
        test_get_task_detail(task_id)
        test_add_comment(task_id)
        test_confirm_task(task_id)
        test_list_records(task_id)
        test_export_tasks(task_id)

    except Exception as exc:
        fail_msg(str(exc))
        return 1

    print_title("7号窗口 smoke test 结果")
    print("PASS: 7")
    print("FAIL: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())