# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/21 12:34
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
# app/tools/log_tool.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
DEFAULT_ASK_LOG_PATH = OUTPUT_DIR / "ask_logs.jsonl"


def safe_json_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, (list, tuple)):
        return [safe_json_value(item) for item in value]

    if isinstance(value, dict):
        return {str(k): safe_json_value(v) for k, v in value.items()}

    if hasattr(value, "model_dump"):
        try:
            return safe_json_value(value.model_dump())
        except Exception:
            pass

    if hasattr(value, "dict"):
        try:
            return safe_json_value(value.dict())
        except Exception:
            pass

    return str(value)


def build_ask_log_record(
    question: str,
    route: str,
    tools_used: list[str],
    answer: str,
    analysis_result: dict[str, Any] | None = None,
    retrieval_result: dict[str, Any] | None = None,
    explanation_result: dict[str, Any] | None = None,
    trace: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "route": route,
        "tools_used": safe_json_value(tools_used),
        "answer": answer,
        "analysis_result": safe_json_value(analysis_result),
        "retrieval_result": safe_json_value(retrieval_result),
        "explanation_result": safe_json_value(explanation_result),
        "trace": safe_json_value(trace or []),
    }


def append_ask_log(
    record: dict[str, Any],
    log_path: Path = DEFAULT_ASK_LOG_PATH,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


__all__ = [
    "DEFAULT_ASK_LOG_PATH",
    "safe_json_value",
    "build_ask_log_record",
    "append_ask_log",
]