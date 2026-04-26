# -*- coding: utf-8 -*-
from __future__ import annotations

"""
7号窗口 smoke test：人工复核中文字段验收

验证目标：
1. assigned_to 可以保存中文
2. reviewer 可以保存中文
3. remark 可以保存中文
4. API 返回不再出现 ???

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

同时，为避免同一个 audit_result_id 已存在未完成任务导致创建冲突，
测试前会先关闭或忽略历史未完成任务。
"""

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


def assert_no_question_marks(value: str | None, field_name: str) -> None:
    if value is None:
        return

    if "???" in value or "????" in value:
        raise AssertionError(f"{field_name} 出现乱码：{value}")


def close_existing_tasks_if_needed() -> None:
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
                    "reviewer": "中文验收脚本",
                    "remark": "中文验收前关闭历史任务",
                },
            )
            continue

        if task_status in {"pending", "processing"}:
            request_raw(
                "POST",
                f"/api/v1/reviews/tasks/{task_id}/ignore",
                json={
                    "reviewer": "中文验收脚本",
                    "remark": "中文验收前忽略历史待处理任务",
                },
            )


def create_review_task() -> int:
    payload = {
        "audit_result_id": AUDIT_RESULT_ID,
        "task_status": "pending",
        "priority": "high",
        "assigned_to": "董宏升",
        "created_by": "中文验收脚本",
    }

    data = request_json(
        "POST",
        "/api/v1/reviews/tasks",
        json=payload,
    )

    task = data["task"]

    assert task["assigned_to"] == "董宏升"
    assert_no_question_marks(task["assigned_to"], "assigned_to")
    assert_no_question_marks(task["created_by"], "created_by")

    task_id = int(task["id"])

    pass_msg(f"中文复核任务创建成功 - task_id={task_id}, assigned_to={task['assigned_to']}")
    return task_id


def add_chinese_comment(task_id: int) -> None:
    payload = {
        "reviewer": "董宏升",
        "remark": "已查看规则依据，等待业务确认。",
    }

    data = request_json(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/comment",
        json=payload,
    )

    records = data["records"]

    target = None
    for record in records:
        if (
            record.get("action_type") == "add_remark"
            and record.get("action_result") == "comment_added"
            and record.get("reviewer") == "董宏升"
            and record.get("remark") == "已查看规则依据，等待业务确认。"
        ):
            target = record
            break

    if target is None:
        raise AssertionError(f"没有找到本次中文备注记录，records={records}")

    assert_no_question_marks(target.get("reviewer"), "reviewer")
    assert_no_question_marks(target.get("remark"), "remark")

    pass_msg("中文备注写入成功")


def confirm_with_chinese(task_id: int) -> None:
    payload = {
        "reviewer": "董宏升",
        "remark": "确认该商品存在规格识别风险，需要业务复核处理。",
    }

    data = request_json(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/confirm",
        json=payload,
    )

    task = data["task"]
    records = data["records"]

    assert task["task_status"] == "confirmed"

    target = None
    for record in records:
        if (
            record.get("action_type") == "confirm_abnormal"
            and record.get("action_result") == "confirmed"
            and record.get("reviewer") == "董宏升"
            and record.get("remark") == "确认该商品存在规格识别风险，需要业务复核处理。"
        ):
            target = record
            break

    if target is None:
        raise AssertionError(f"没有找到本次中文确认记录，records={records}")

    assert_no_question_marks(target.get("reviewer"), "confirm.reviewer")
    assert_no_question_marks(target.get("remark"), "confirm.remark")

    pass_msg("中文确认异常动作成功 - task_status=confirmed")


def check_export(task_id: int) -> None:
    data = request_json(
        "GET",
        "/api/v1/reviews/export",
    )

    items = data["items"]
    target = None

    for item in items:
        if item["task_id"] == task_id:
            target = item
            break

    if target is None:
        raise AssertionError(f"导出结果中没有 task_id={task_id}")

    assert_no_question_marks(target.get("assigned_to"), "export.assigned_to")
    assert_no_question_marks(target.get("latest_reviewer"), "export.latest_reviewer")
    assert_no_question_marks(target.get("latest_remark"), "export.latest_remark")

    pass_msg("中文导出结果验收成功")


def main() -> int:
    print_title("7号窗口 smoke test：人工复核中文字段验收")

    try:
        close_existing_tasks_if_needed()

        task_id = create_review_task()
        add_chinese_comment(task_id)
        confirm_with_chinese(task_id)
        check_export(task_id)

    except Exception as exc:
        fail_msg(str(exc))
        return 1

    print_title("7号窗口中文字段验收结果")
    print("PASS: 4")
    print("FAIL: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())