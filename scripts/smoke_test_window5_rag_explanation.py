# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/24 22:46
IDE       :PyCharm
作者      :董宏升

5号窗口 smoke test：RAG 检索解释层验收脚本

验证范围：
1. retrieval_service 是否支持 baseline / vector / hybrid；
2. 检索结果是否包含 metadata / score_reasons / citation 所需字段；
3. rule_explanation_service 是否能完成：
   audit_result -> rule_hit -> rule_definition -> rule_chunk -> evidence -> citation；
4. low_price 命中解释链是否可用；
5. cross_platform_gap 命中解释链是否可用；
6. spec_risk 如果存在正向命中样本，则执行完整解释链；
   如果当前数据库没有 spec_risk is_hit=1 样本，则 SKIP，并输出说明。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.audit_result import AuditResult
from app.models.rule_hit import RuleHit
from app.rag.retrieval_service import search_rules_simple
from app.rag.rule_explanation_service import explain_audit_result
from app.rag.schemas import EvidenceType, RetrievalMode


@dataclass
class SmokeResult:
    name: str
    status: str
    message: str


def print_header(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def print_result(result: SmokeResult) -> None:
    print(f"[{result.status}] {result.name} - {result.message}")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def find_hit_audit_result_id(
        db: Session,
        anomaly_type: str,
) -> int | None:
    """
    查找某类异常的正向命中样本。

    要求：
    1. audit_result.is_hit = true；
    2. rule_hit.is_hit = true；
    3. audit_result.anomaly_type 匹配。
    """
    row = (
        db.query(AuditResult.id)
        .join(RuleHit, RuleHit.audit_result_id == AuditResult.id)
        .filter(
            AuditResult.anomaly_type == anomaly_type,
            AuditResult.is_hit.is_(True),
            RuleHit.is_hit.is_(True),
        )
        .group_by(AuditResult.id)
        .order_by(AuditResult.id.asc())
        .first()
    )

    if row is None:
        return None

    return int(row[0])


def check_retrieval_result_common(response, expected_mode: RetrievalMode) -> None:
    assert_true(response.retrieval_mode == expected_mode, "retrieval_mode 不符合预期")
    assert_true(response.total > 0, "检索结果为空")
    assert_true(len(response.results) > 0, "results 为空")
    assert_true(len(response.trace_notes) > 0, "trace_notes 为空")

    first = response.results[0]

    assert_true(first.chunk_id is not None, "chunk_id 为空")
    assert_true(first.doc_title is not None, "doc_title 为空")
    assert_true(first.section_title is not None, "section_title 为空")
    assert_true(first.preview_text is not None, "preview_text 为空")
    assert_true(len(first.score_reasons) > 0, "score_reasons 为空")

    # rerank 预留必须接入
    assert_true(
        any("rerank" in reason for reason in first.score_reasons),
        "score_reasons 中未发现 rerank 预留标记",
    )


def smoke_test_retrieval_modes() -> list[SmokeResult]:
    results: list[SmokeResult] = []

    cases = [
        ("baseline 检索低价规则", "低价异常是怎么判断的？", RetrievalMode.BASELINE),
        ("vector 检索低价规则", "低价异常是怎么判断的？", RetrievalMode.VECTOR),
        ("hybrid 检索低价规则", "低价异常是怎么判断的？", RetrievalMode.HYBRID),
        ("hybrid 检索跨平台价差规则", "跨平台价差规则是什么？", RetrievalMode.HYBRID),
        ("hybrid 检索规格风险规则", "规格识别风险一般什么情况下会命中？", RetrievalMode.HYBRID),
        ("hybrid 检索人工复核流程", "业务人员看到异常后应该怎么复核？", RetrievalMode.HYBRID),
    ]

    for name, query, mode in cases:
        try:
            response = search_rules_simple(
                query=query,
                top_k=3,
                retrieval_mode=mode,
                rerank_enabled=False,
            )

            check_retrieval_result_common(response, expected_mode=mode)

            results.append(
                SmokeResult(
                    name=name,
                    status="PASS",
                    message=f"返回 {response.total} 条结果，mode={response.retrieval_mode.value}",
                )
            )

        except Exception as exc:
            results.append(
                SmokeResult(
                    name=name,
                    status="FAIL",
                    message=str(exc),
                )
            )

    return results


def check_explanation_common(explanation, expected_anomaly_type: str) -> None:
    assert_true(explanation.audit_result_id is not None, "audit_result_id 为空")
    assert_true(explanation.clean_id is not None, "clean_id 为空")
    assert_true(explanation.anomaly_type == expected_anomaly_type, "anomaly_type 不符合预期")
    assert_true(bool(explanation.final_summary), "final_summary 为空")
    assert_true(explanation.rule_facts is not None, "rule_facts 为空")

    evidence_types = {item.evidence_type for item in explanation.evidences}

    assert_true(EvidenceType.AUDIT_RESULT in evidence_types, "缺少 audit_result evidence")
    assert_true(EvidenceType.RULE_HIT in evidence_types, "缺少 rule_hit evidence")
    assert_true(EvidenceType.RULE_DEFINITION in evidence_types, "缺少 rule_definition evidence")
    assert_true(EvidenceType.RULE_CHUNK in evidence_types, "缺少 rule_chunk evidence")

    assert_true(len(explanation.citations) > 0, "citations 为空")
    assert_true(len(explanation.trace_notes) > 0, "trace_notes 为空")

    first_citation = explanation.citations[0]
    assert_true(first_citation.doc_title is not None, "citation.doc_title 为空")
    assert_true(first_citation.section_title is not None, "citation.section_title 为空")
    assert_true(first_citation.chunk_id is not None, "citation.chunk_id 为空")
    assert_true(first_citation.source_doc_path is not None, "citation.source_doc_path 为空")


def smoke_test_explanation(db: Session, anomaly_type: str) -> SmokeResult:
    """
    测试指定 anomaly_type 的正向命中解释链。
    """
    audit_result_id = find_hit_audit_result_id(db=db, anomaly_type=anomaly_type)

    if audit_result_id is None:
        return SmokeResult(
            name=f"{anomaly_type} 命中解释链",
            status="SKIP",
            message=f"当前数据库没有 {anomaly_type} 的 is_hit=1 正向命中样本。",
        )

    try:
        explanation = explain_audit_result(
            db=db,
            audit_result_id=audit_result_id,
            retrieval_mode=RetrievalMode.HYBRID,
            chunk_top_k=2,
            rerank_enabled=False,
        )

        check_explanation_common(
            explanation=explanation,
            expected_anomaly_type=anomaly_type,
        )

        return SmokeResult(
            name=f"{anomaly_type} 命中解释链",
            status="PASS",
            message=(
                f"audit_result_id={audit_result_id}, "
                f"evidences={len(explanation.evidences)}, "
                f"citations={len(explanation.citations)}"
            ),
        )

    except Exception as exc:
        return SmokeResult(
            name=f"{anomaly_type} 命中解释链",
            status="FAIL",
            message=f"audit_result_id={audit_result_id}, error={exc}",
        )


def count_spec_risk_status(db: Session) -> dict[str, int]:
    """
    统计 spec_risk 当前数据状态。
    """
    audit_total = (
            db.query(func.count(AuditResult.id))
            .filter(AuditResult.anomaly_type == "spec_risk")
            .scalar()
            or 0
    )

    audit_hit = (
            db.query(func.count(AuditResult.id))
            .filter(
                AuditResult.anomaly_type == "spec_risk",
                AuditResult.is_hit.is_(True),
            )
            .scalar()
            or 0
    )

    rule_hit_total = (
            db.query(func.count(RuleHit.id))
            .filter(RuleHit.anomaly_type == "spec_risk")
            .scalar()
            or 0
    )

    rule_hit_positive = (
            db.query(func.count(RuleHit.id))
            .filter(
                RuleHit.anomaly_type == "spec_risk",
                RuleHit.is_hit.is_(True),
            )
            .scalar()
            or 0
    )

    return {
        "spec_audit_total": int(audit_total),
        "spec_audit_hit": int(audit_hit),
        "spec_rule_hit_total": int(rule_hit_total),
        "spec_rule_hit_positive": int(rule_hit_positive),
    }


def main() -> None:
    all_results: list[SmokeResult] = []

    print_header("5号窗口 smoke test：retrieval service")
    retrieval_results = smoke_test_retrieval_modes()
    all_results.extend(retrieval_results)

    for item in retrieval_results:
        print_result(item)

    db = SessionLocal()

    try:
        print_header("5号窗口 smoke test：rule explanation service")

        for anomaly_type in ["low_price", "cross_platform_gap", "spec_risk"]:
            result = smoke_test_explanation(db=db, anomaly_type=anomaly_type)
            all_results.append(result)
            print_result(result)

        print_header("spec_risk 当前数据状态")
        spec_status = count_spec_risk_status(db=db)
        for key, value in spec_status.items():
            print(f"{key}: {value}")

        if spec_status["spec_rule_hit_positive"] == 0:
            print(
                "\n[INFO] 当前数据库存在 spec_risk 检查记录，但没有 spec_risk 正向命中样本。"
            )
            print(
                "[INFO] 5号窗口先将 spec_risk 命中解释链记为 SKIP；"
                "后续需要回到 4号窗口补 SPEC_RISK 正向样本后复测。"
            )

    finally:
        db.close()

    print_header("5号窗口 smoke test 汇总")

    pass_count = sum(1 for item in all_results if item.status == "PASS")
    fail_count = sum(1 for item in all_results if item.status == "FAIL")
    skip_count = sum(1 for item in all_results if item.status == "SKIP")

    print(f"PASS: {pass_count}")
    print(f"FAIL: {fail_count}")
    print(f"SKIP: {skip_count}")

    if fail_count > 0:
        print("\n存在 FAIL 项，请先处理失败项。")
        raise SystemExit(1)

    print("\n5号窗口 smoke test 执行完成。")


if __name__ == "__main__":
    main()
