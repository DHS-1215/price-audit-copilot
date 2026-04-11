# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/11 09:37
IDE       :PyCharm
作者      :董宏升

第四周：问答日志工具层

该模块目标不是做复杂日志系统，而是给统一 ask 入口补一个“最小可用的落盘日志能力”。

考虑到第四周 ask 已经不是单步接口了，而是会路由问题、调 analysis / retrieval / explanation / report 等工具、返回结构化结果和 trace
如果这些信息只存在接口响应里，那一旦后面我想复盘、调试、做验收、录demo，会很难追踪“某次问答到底发生了什么”。
所以把每次 /ask 的核心写入 jsonl 文件。（jsonl：一行一条记录、易读、易追加）
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import json
from datetime import datetime
from pathlib import Path
from typing import Any
import math

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 日志输出目录
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"

# 问答日志文件
ASK_LOG_PATH = OUTPUT_DIR / "ask_logs.jsonl"

"""1. 小工具"""


# 把对象尽量转成能写进Json的格式
def safe_json_value(value: Any) -> Any:
    """
    因为 AskResponse 里有些字段可能是，字典、列表、pydantic model、其他python对象，JSONL落盘时，最好尽量保证每个字段可序列化。
    """

    # 1. None 直接保留
    if value is None:
        return None

    # 2. bool 要放在 int 前面判断
    #    因为 bool 是 int 的子类
    if isinstance(value, bool):
        return value

    # 3. 字符串直接返回
    if isinstance(value, str):
        return value

    # 4. int 直接返回
    if isinstance(value, int):
        return value

    # 5. float 单独处理
    if isinstance(value, float):
        # NaN / 正负无穷都统一转成 None
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    # 6. list / tuple 递归处理
    if isinstance(value, (list, tuple)):
        return [safe_json_value(item) for item in value]

    # 7. dict 递归处理
    if isinstance(value, dict):
        return {str(k): safe_json_value(v) for k, v in value.items()}

    # 8. Pydantic v2 常见对象
    if hasattr(value, "model_dump"):
        try:
            return safe_json_value(value.model_dump())
        except Exception:
            pass

    # 9. 兼容旧式对象
    if hasattr(value, "dict"):
        try:
            return safe_json_value(value.dict())
        except Exception:
            pass

    # 10. 兜底转字符串
    return str(value)


# 组装日志问答系统
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
    """
    :param question: 用户问题
    :param route: 路由结果
    :param tools_used: 调用工具
    :param answer: 最终答案
    :param analysis_result: 分析结果
    :param retrieval_result: 检索结果
    :param explanation_result: 解释结果
    :param trace: trace 链路
    """
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


# 把单条日志追加写入 ask_logs.jsonl.
def append_ask_log(record: dict[str, Any], log_path: Path = ASK_LOG_PATH) -> None:
    """
    该函数目的：问答日志通常是一条条积累，没必要每次全量重写。
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
