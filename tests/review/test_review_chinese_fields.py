# -*- coding: utf-8 -*-
from __future__ import annotations

"""
8号窗口 pytest：人工复核中文字段测试

测试目标：
1. assigned_to 可以保存中文
2. created_by 可以保存中文
3. reviewer 可以保存中文
4. remark 可以保存中文
5. export 导出结果中文字段不乱码

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


def assert_no_question_marks(value: str | None, field_name: str) -> None:
    if value is None:
        return

    assert "???" not in value, f"{field_name} 出现乱码：{value}"
    assert "????" not in value, f"{field_name} 出现乱码：{value}"


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
                    "reviewer": "中文pytest",
                    "remark": "中文 pytest 前关闭历史任务",
                },
            )
            continue

        if task_status in {"pending", "processing"}:
            request_raw(
                "POST",
                f"/api/v1/reviews/tasks/{task_id}/ignore",
                json={
                    "reviewer": "中文pytest",
                    "remark": "中文 pytest 前忽略历史待处理任务",
                },
            )


def test_review_chinese_fields_can_be_saved_and_exported() -> None:
    close_existing_tasks_if_needed()

    create_data = request_json_ok(
        "POST",
        "/api/v1/reviews/tasks",
        json={
            "audit_result_id": AUDIT_RESULT_ID,
            "task_status": "pending",
            "priority": "high",
            "assigned_to": "董宏升",
            "created_by": "中文pytest",
        },
    )

    task = create_data["task"]
    task_id = int(task["id"])

    assert task["assigned_to"] == "董宏升"
    assert task["created_by"] == "中文pytest"
    assert_no_question_marks(task["assigned_to"], "assigned_to")
    assert_no_question_marks(task["created_by"], "created_by")

    comment_data = request_json_ok(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/comment",
        json={
            "reviewer": "董宏升",
            "remark": "已查看规则依据，等待业务确认。",
        },
    )

    comment_records = comment_data["records"]
    comment_target = None

    for record in comment_records:
        if (
            record.get("action_type") == "add_remark"
            and record.get("reviewer") == "董宏升"
            and record.get("remark") == "已查看规则依据，等待业务确认。"
        ):
            comment_target = record
            break

    assert comment_target is not None, comment_records
    assert_no_question_marks(comment_target.get("reviewer"), "comment.reviewer")
    assert_no_question_marks(comment_target.get("remark"), "comment.remark")

    confirm_data = request_json_ok(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/confirm",
        json={
            "reviewer": "董宏升",
            "remark": "确认该商品存在规格识别风险，需要业务复核处理。",
        },
    )

    assert confirm_data["task"]["task_status"] == "confirmed"

    confirm_records = confirm_data["records"]
    confirm_target = None

    for record in confirm_records:
        if (
            record.get("action_type") == "confirm_abnormal"
            and record.get("reviewer") == "董宏升"
            and record.get("remark") == "确认该商品存在规格识别风险，需要业务复核处理。"
        ):
            confirm_target = record
            break

    assert confirm_target is not None, confirm_records
    assert_no_question_marks(confirm_target.get("reviewer"), "confirm.reviewer")
    assert_no_question_marks(confirm_target.get("remark"), "confirm.remark")

    export_data = request_json_ok(
        "GET",
        "/api/v1/reviews/export",
    )

    target = None
    for item in export_data["items"]:
        if item.get("task_id") == task_id:
            target = item
            break

    assert target is not None, export_data["items"]

    assert_no_question_marks(target.get("assigned_to"), "export.assigned_to")
    assert_no_question_marks(target.get("latest_reviewer"), "export.latest_reviewer")
    assert_no_question_marks(target.get("latest_remark"), "export.latest_remark")