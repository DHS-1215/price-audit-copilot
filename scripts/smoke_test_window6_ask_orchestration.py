# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/25 11:46
IDE       :PyCharm
作者      :董宏升

6号窗口 smoke test：统一问答编排层

测试目标：
1. /ask analysis 主链
2. /ask retrieval 正式 retrieval_service
3. /ask explanation 正式 rule_explanation_service
4. /ask explanation fallback 兼容链
5. /ask mixed 受控编排链
6. /ask-lc mixed LangChain 增强链强制 report tool
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import traceback
from typing import Any

from app.schemas.ask import AskRequest
from app.orchestrators.ask_orchestrator import run_ask
from app.orchestrators.ask_lc_orchestrator import run_langchain_ask

PASS_COUNT = 0
FAIL_COUNT = 0


def print_title(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def pass_case(name: str, detail: str = "") -> None:
    global PASS_COUNT
    PASS_COUNT += 1
    if detail:
        print(f"[PASS] {name} - {detail}")
    else:
        print(f"[PASS] {name}")


def fail_case(name: str, error: str) -> None:
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"[FAIL] {name} - {error}")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {"value": value}


def test_ask_analysis() -> None:
    name = "/ask analysis 路由"

    req = AskRequest(
        question="当前异常情况统计一下",
        top_k=3,
        use_vector=False,
        include_trace=True,
    )

    response = run_ask(req)
    data = as_dict(response)

    assert_true(data["route"] == "analysis", f"route 应为 analysis，实际为 {data['route']}")
    assert_true("analysis_tools" in data["tools_used"], "tools_used 应包含 analysis_tools")
    assert_true(data["analysis_result"] is not None, "analysis_result 不应为空")
    assert_true(data["analysis_result"]["stats"]["anomaly_count"] >= 0, "anomaly_count 应存在")

    pass_case(name, data["answer"])


def test_ask_retrieval() -> None:
    name = "/ask retrieval 正式检索服务"

    req = AskRequest(
        question="低价异常规则是怎么判断的？",
        top_k=3,
        use_vector=False,
        include_trace=True,
    )

    response = run_ask(req)
    data = as_dict(response)

    assert_true(data["route"] == "retrieval", f"route 应为 retrieval，实际为 {data['route']}")
    assert_true("retrieval_service" in data["tools_used"], "tools_used 应包含 retrieval_service")
    assert_true(data["retrieval_mode"] == "hybrid", f"retrieval_mode 应为 hybrid，实际为 {data['retrieval_mode']}")

    retrieval_result = data["retrieval_result"]
    assert_true(retrieval_result is not None, "retrieval_result 不应为空")
    assert_true(len(retrieval_result.get("results", [])) > 0, "retrieval_result.results 不应为空")

    top = retrieval_result["results"][0]
    detail = f"mode={data['retrieval_mode']}, top_doc={top.get('doc_title')}, top_section={top.get('section_title')}"
    pass_case(name, detail)


def test_ask_explanation_formal() -> None:
    name = "/ask explanation 正式解释链"

    req = AskRequest(
        question="audit_result_id=259 为什么被判规格风险？",
        top_k=2,
        use_vector=False,
        include_trace=True,
        audit_result_id=259,
    )

    response = run_ask(req)
    data = as_dict(response)

    assert_true(data["route"] == "explanation", f"route 应为 explanation，实际为 {data['route']}")
    assert_true("rule_explanation_service" in data["tools_used"], "tools_used 应包含 rule_explanation_service")
    assert_true(data["retrieval_mode"] == "hybrid", f"retrieval_mode 应为 hybrid，实际为 {data['retrieval_mode']}")

    explanation_result = data["explanation_result"]
    assert_true(explanation_result is not None, "explanation_result 不应为空")
    assert_true(explanation_result.get("rule_facts") is not None, "rule_facts 不应为空")
    assert_true(len(explanation_result.get("evidences", [])) > 0, "evidences 不应为空")
    assert_true(len(explanation_result.get("citations", [])) > 0, "citations 不应为空")

    detail = (
        f"audit_result_id={explanation_result.get('audit_result_id')}, "
        f"citations={len(explanation_result.get('citations', []))}"
    )
    pass_case(name, detail)


def test_ask_explanation_fallback() -> None:
    name = "/ask explanation fallback 兼容链"

    req = AskRequest(
        question="为什么这个商品会被判成低价异常？",
        top_k=3,
        use_vector=False,
        include_trace=True,
    )

    response = run_ask(req)
    data = as_dict(response)

    assert_true(data["route"] == "explanation", f"route 应为 explanation，实际为 {data['route']}")
    assert_true("explanation_tools_fallback" in data["tools_used"], "tools_used 应包含 explanation_tools_fallback")
    assert_true(data["explanation_result"] is not None, "explanation_result 不应为空")
    assert_true(data["retrieval_result"] is not None, "retrieval_result 不应为空")

    pass_case(name, "fallback explanation_result / retrieval_result 均正常返回")


def test_ask_mixed() -> None:
    name = "/ask mixed 受控编排链"

    req = AskRequest(
        question="先统计当前异常情况，再结合规则写一段简短汇报",
        top_k=3,
        use_vector=False,
        include_trace=True,
    )

    response = run_ask(req)
    data = as_dict(response)

    assert_true(data["route"] == "mixed", f"route 应为 mixed，实际为 {data['route']}")
    assert_true("analysis_tools" in data["tools_used"], "tools_used 应包含 analysis_tools")
    assert_true("retrieval_service" in data["tools_used"], "tools_used 应包含 retrieval_service")
    assert_true("report_tools" in data["tools_used"], "tools_used 应包含 report_tools")
    assert_true(data["analysis_result"] is not None, "analysis_result 不应为空")
    assert_true(data["retrieval_result"] is not None, "retrieval_result 不应为空")
    assert_true(data["retrieval_mode"] == "hybrid", f"retrieval_mode 应为 hybrid，实际为 {data['retrieval_mode']}")

    retrieval_query = data["retrieval_result"].get("query")
    assert_true("规则" in retrieval_query, f"mixed retrieval_query 应更聚焦规则，实际为：{retrieval_query}")

    pass_case(name, f"retrieval_query={retrieval_query}")


def test_ask_lc_mixed() -> None:
    name = "/ask-lc mixed 增强链"

    result = run_langchain_ask(
        question="先统计当前异常情况，再写一段简短汇报",
        top_k=3,
        use_vector=False,
    )

    assert_true(result.get("ok") is True, "ok 应为 true")
    assert_true(result.get("task_type") == "mixed", f"task_type 应为 mixed，实际为 {result.get('task_type')}")
    assert_true(result.get("answer"), "answer 不应为空")

    raw_result = result.get("raw_result") or {}
    assert_true(raw_result.get("forced_tool") == "build_report_tool", "mixed 应强制走 build_report_tool")

    pass_case(name, "forced_tool=build_report_tool")


def run_case(case_func) -> None:
    try:
        case_func()
    except Exception as e:
        fail_case(case_func.__name__, f"{type(e).__name__}: {e}")
        traceback.print_exc()


def main() -> None:
    print_title("6号窗口 smoke test：/ask 主链与 /ask-lc 增强链")

    cases = [
        test_ask_analysis,
        test_ask_retrieval,
        test_ask_explanation_formal,
        test_ask_explanation_fallback,
        test_ask_mixed,
        test_ask_lc_mixed,
    ]

    for case in cases:
        run_case(case)

    print_title("6号窗口 smoke test 结果")
    print(f"PASS: {PASS_COUNT}")
    print(f"FAIL: {FAIL_COUNT}")

    if FAIL_COUNT > 0:
        raise SystemExit(1)

    print("\n全部通过，6号窗口 ask 编排层主链与增强链验证完成。")


if __name__ == "__main__":
    main()
