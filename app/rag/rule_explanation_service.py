# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/24 22:20
IDE       :PyCharm
作者      :董宏升

5号窗口：规则解释服务

本模块负责把规则解释链正式串起来：

audit_result -> rule_hit -> rule_definition -> rule_chunk -> evidence -> citation

职责边界：
1. 不重新判定异常；
2. 不覆盖 4号窗口的 audit_result / rule_hit 事实；
3. 不绕开 rule_definition 自己解释规则；
4. 只在结果事实和规则定义基础上，检索 rule_chunk 作为文档依据；
5. 输出 ExplanationSchema，交给后续 6号窗口 /ask 编排层使用。

注意：
本服务不是 /ask 总编排，不负责问题路由，也不负责 mixed 流程。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import argparse
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.audit_result import AuditResult
from app.models.rule_definition import RuleDefinition
from app.models.rule_hit import RuleHit
from app.rag.retrieval_service import search_rules
from app.rag.schemas import (
    CitationSchema,
    EvidenceSchema,
    EvidenceType,
    ExplanationSchema,
    RetrievalMode,
    RetrievalQuery,
    RuleFactSchema,
    citation_from_evidence,
    build_preview_text,
)


def to_jsonable(value: Any) -> Any:
    """
    将 Decimal / datetime 等对象转为 JSON 可序列化结构。
    """
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}

    if isinstance(value, list):
        return [to_jsonable(item) for item in value]

    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]

    return value


def get_audit_result(
        db: Session,
        audit_result_id: int | None = None,
        clean_id: int | None = None,
        anomaly_type: str | None = None,
) -> AuditResult:
    """
    获取 audit_result。

    优先使用 audit_result_id。
    如果没有 audit_result_id，则用 clean_id + anomaly_type 查最新一条。
    """
    if audit_result_id is not None:
        audit_result = (
            db.query(AuditResult)
            .filter(AuditResult.id == audit_result_id)
            .first()
        )
        if audit_result is None:
            raise ValueError(f"未找到 audit_result：id={audit_result_id}")
        return audit_result

    if clean_id is None:
        raise ValueError("audit_result_id 和 clean_id 至少需要提供一个。")

    query = db.query(AuditResult).filter(AuditResult.clean_id == clean_id)

    if anomaly_type:
        query = query.filter(AuditResult.anomaly_type == anomaly_type)

    audit_result = query.order_by(AuditResult.id.desc()).first()

    if audit_result is None:
        raise ValueError(
            f"未找到 audit_result：clean_id={clean_id}, anomaly_type={anomaly_type}"
        )

    return audit_result


def get_rule_hits(db: Session, audit_result: AuditResult) -> list[RuleHit]:
    """
    获取某条 audit_result 对应的 rule_hit。

    默认只取 is_hit=True 的命中明细。
    如果没有命中明细，再退一步取该 audit_result 下全部 rule_hit。
    """
    hit_rows = (
        db.query(RuleHit)
        .filter(
            RuleHit.audit_result_id == audit_result.id,
            RuleHit.is_hit.is_(True),
        )
        .order_by(RuleHit.hit_order.asc(), RuleHit.id.asc())
        .all()
    )

    if hit_rows:
        return hit_rows

    return (
        db.query(RuleHit)
        .filter(RuleHit.audit_result_id == audit_result.id)
        .order_by(RuleHit.hit_order.asc(), RuleHit.id.asc())
        .all()
    )


def get_rule_definitions(
        db: Session,
        audit_result: AuditResult,
        rule_hits: list[RuleHit],
) -> list[RuleDefinition]:
    """
    获取解释链相关的 rule_definition。

    来源：
    1. audit_result.rule_definition_id；
    2. rule_hit.rule_definition_id；
    3. rule_hit.rule_code + rule_hit.rule_version 兜底查找。
    """
    definitions: list[RuleDefinition] = []
    seen_ids: set[int] = set()

    definition_ids: set[int] = set()

    if audit_result.rule_definition_id:
        definition_ids.add(audit_result.rule_definition_id)

    for hit in rule_hits:
        if hit.rule_definition_id:
            definition_ids.add(hit.rule_definition_id)

    if definition_ids:
        rows = (
            db.query(RuleDefinition)
            .filter(RuleDefinition.id.in_(definition_ids))
            .all()
        )
        for row in rows:
            if row.id not in seen_ids:
                definitions.append(row)
                seen_ids.add(row.id)

    for hit in rule_hits:
        exists = any(
            item.rule_code == hit.rule_code and item.version == hit.rule_version
            for item in definitions
        )
        if exists:
            continue

        row = (
            db.query(RuleDefinition)
            .filter(
                RuleDefinition.rule_code == hit.rule_code,
                RuleDefinition.version == hit.rule_version,
            )
            .first()
        )
        if row and row.id not in seen_ids:
            definitions.append(row)
            seen_ids.add(row.id)

    return definitions


def build_rule_fact(
        audit_result: AuditResult,
        rule_hits: list[RuleHit],
) -> RuleFactSchema:
    """
    构建结果层事实摘要。

    注意：
    rule_facts 只总结 4号窗口已经确定的事实，不做新判定。
    """
    hit_messages = [
        hit.hit_message
        for hit in rule_hits
        if hit.hit_message
    ]

    first_hit = rule_hits[0] if rule_hits else None

    input_snapshot = None
    threshold_snapshot = None
    computed_value = None

    if first_hit:
        input_snapshot = first_hit.input_snapshot_json
        threshold_snapshot = first_hit.threshold_snapshot_json
        computed_value = first_hit.computed_value_json
    else:
        input_snapshot = audit_result.input_snapshot_json

    return RuleFactSchema(
        audit_result_id=audit_result.id,
        clean_id=audit_result.clean_id,
        anomaly_type=audit_result.anomaly_type,
        is_hit=audit_result.is_hit,
        hit_rule_code=audit_result.hit_rule_code,
        hit_rule_version=audit_result.hit_rule_version,
        reason_text=audit_result.reason_text,
        hit_messages=hit_messages,
        input_snapshot=to_jsonable(input_snapshot),
        threshold_snapshot=to_jsonable(threshold_snapshot),
        computed_value=to_jsonable(computed_value),
    )


def build_audit_result_evidence(audit_result: AuditResult) -> EvidenceSchema:
    """
    将 audit_result 转为 evidence。
    """
    preview = (
            audit_result.reason_text
            or f"clean_id={audit_result.clean_id} 的 {audit_result.anomaly_type} 判定结果：is_hit={audit_result.is_hit}"
    )

    computed_value: dict[str, Any] = {
        "explicit_low_price_threshold": audit_result.explicit_low_price_threshold,
        "group_avg_price": audit_result.group_avg_price,
        "price_to_group_avg_ratio": audit_result.price_to_group_avg_ratio,
        "low_price_rule_source": audit_result.low_price_rule_source,
    }

    return EvidenceSchema(
        evidence_id=f"audit_result:audit_result:{audit_result.id}",
        evidence_type=EvidenceType.AUDIT_RESULT,
        source_table="audit_result",
        source_id=audit_result.id,
        rule_code=audit_result.hit_rule_code,
        rule_version=audit_result.hit_rule_version,
        anomaly_type=audit_result.anomaly_type,
        preview_text=build_preview_text(preview),
        input_snapshot=to_jsonable(audit_result.input_snapshot_json),
        computed_value=to_jsonable(computed_value),
        score_reasons=["audit_result_fact"],
        trace_note="来自 audit_result 的结果层事实。",
    )


def build_rule_hit_evidence(rule_hit: RuleHit) -> EvidenceSchema:
    """
    将 rule_hit 转为 evidence。
    """
    preview = (
            rule_hit.hit_message
            or f"规则 {rule_hit.rule_code} 命中状态：is_hit={rule_hit.is_hit}"
    )

    return EvidenceSchema(
        evidence_id=f"rule_hit:rule_hit:{rule_hit.id}",
        evidence_type=EvidenceType.RULE_HIT,
        source_table="rule_hit",
        source_id=rule_hit.id,
        rule_code=rule_hit.rule_code,
        rule_version=rule_hit.rule_version,
        anomaly_type=rule_hit.anomaly_type,
        preview_text=build_preview_text(preview),
        input_snapshot=to_jsonable(rule_hit.input_snapshot_json),
        threshold_snapshot=to_jsonable(rule_hit.threshold_snapshot_json),
        computed_value=to_jsonable(rule_hit.computed_value_json),
        score_reasons=["rule_hit_fact"],
        trace_note="来自 rule_hit 的规则命中明细。",
    )


def build_rule_definition_evidence(
        rule_definition: RuleDefinition,
) -> EvidenceSchema:
    """
    将 rule_definition 转为 evidence。
    """
    preview = " / ".join(
        item
        for item in [
            rule_definition.rule_code,
            rule_definition.rule_name,
            rule_definition.description,
        ]
        if item
    )

    return EvidenceSchema(
        evidence_id=f"rule_definition:rule_definition:{rule_definition.id}",
        evidence_type=EvidenceType.RULE_DEFINITION,
        source_table="rule_definition",
        source_id=rule_definition.id,
        rule_code=rule_definition.rule_code,
        rule_version=rule_definition.version,
        anomaly_type=rule_definition.rule_type,
        source_doc_path=rule_definition.source_doc_path,
        preview_text=build_preview_text(preview),
        threshold_snapshot=to_jsonable(rule_definition.threshold_config_json),
        score_reasons=["rule_definition_fact"],
        trace_note="来自 rule_definition 的正式规则定义。",
    )


def build_rule_chunk_evidence_from_retrieval(
        item: Any,
        index: int,
) -> EvidenceSchema:
    """
    将 RetrievalResult 转为 rule_chunk evidence。
    """
    return EvidenceSchema(
        evidence_id=f"rule_chunk:retrieval:{item.chunk_id}:{index}",
        evidence_type=EvidenceType.RULE_CHUNK,
        source_table="rule_chunk",
        source_id=item.chunk_id,
        rule_code=item.rule_code,
        rule_version=item.rule_version,
        anomaly_type=item.anomaly_type,
        doc_title=item.doc_title,
        section_title=item.section_title,
        section_path=item.section_path,
        chunk_id=item.chunk_id,
        source_doc_path=item.source_doc_path,
        preview_text=item.preview_text,
        score=item.final_score,
        score_reasons=list(item.score_reasons),
        metadata=to_jsonable(item.metadata),
        trace_note="来自 retrieval_service 检索到的 rule_chunk 文档依据。",
    )


def build_explanation_query(
        audit_result: AuditResult,
        rule_hit: RuleHit | None = None,
        rule_definition: RuleDefinition | None = None,
) -> str:
    """
    构建用于检索 rule_chunk 的查询文本。

    注意：
    query 只是辅助召回，真正的强约束来自 rule_code / rule_version / anomaly_type。
    """
    parts: list[str] = []

    if audit_result.reason_text:
        parts.append(audit_result.reason_text)

    if rule_hit:
        parts.extend(
            [
                rule_hit.rule_code,
                rule_hit.rule_version,
                rule_hit.anomaly_type,
                rule_hit.hit_message or "",
            ]
        )

    if rule_definition:
        parts.extend(
            [
                rule_definition.rule_code,
                rule_definition.rule_name,
                rule_definition.description or "",
            ]
        )

    if not parts:
        parts.append(audit_result.anomaly_type)

    return " ".join(str(part) for part in parts if part).strip()


def find_definition_for_hit(
        rule_hit: RuleHit,
        rule_definitions: list[RuleDefinition],
) -> RuleDefinition | None:
    """
    根据 rule_hit 找到对应 rule_definition。
    """
    if rule_hit.rule_definition_id:
        for item in rule_definitions:
            if item.id == rule_hit.rule_definition_id:
                return item

    for item in rule_definitions:
        if item.rule_code == rule_hit.rule_code and item.version == rule_hit.rule_version:
            return item

    return None


def build_final_summary(
        audit_result: AuditResult,
        rule_hits: list[RuleHit],
        citations: list[CitationSchema],
) -> str:
    """
    构建最终解释摘要。

    这里只做确定性摘要，不让模型自由发挥。
    """
    if not audit_result.is_hit:
        return (
            f"clean_id={audit_result.clean_id} 当前未命中 {audit_result.anomaly_type} 异常。"
            " 本解释仅展示已有规则检查事实，不代表发现异常。"
        )

    hit_codes = [hit.rule_code for hit in rule_hits if hit.is_hit]
    hit_codes_text = "、".join(dict.fromkeys(hit_codes)) if hit_codes else audit_result.hit_rule_code

    reason = audit_result.reason_text or ""
    citation_text = f" 已补充 {len(citations)} 条规则文档引用。" if citations else " 当前未找到可展示的规则文档引用。"

    return (
        f"clean_id={audit_result.clean_id} 命中 {audit_result.anomaly_type} 异常，"
        f"主要命中规则为 {hit_codes_text or '未记录'}。"
        f"{' 原因摘要：' + reason if reason else ''}"
        f"{citation_text}"
    )


def dedup_evidences(evidences: list[EvidenceSchema]) -> list[EvidenceSchema]:
    """
    evidence 去重。
    """
    seen: set[str] = set()
    result: list[EvidenceSchema] = []

    for evidence in evidences:
        key = evidence.evidence_id
        if key in seen:
            continue
        seen.add(key)
        result.append(evidence)

    return result


def explain_audit_result(
        db: Session,
        audit_result_id: int | None = None,
        clean_id: int | None = None,
        anomaly_type: str | None = None,
        retrieval_mode: RetrievalMode = RetrievalMode.HYBRID,
        chunk_top_k: int = 2,
        rerank_enabled: bool = False,
) -> ExplanationSchema:
    """
    规则解释主入口。

    固定链路：
    audit_result -> rule_hit -> rule_definition -> rule_chunk -> evidence -> citation
    """
    audit_result = get_audit_result(
        db=db,
        audit_result_id=audit_result_id,
        clean_id=clean_id,
        anomaly_type=anomaly_type,
    )

    trace_notes: list[str] = [
        "解释链路固定为 audit_result -> rule_hit -> rule_definition -> rule_chunk。",
        "本服务不重新判定异常，只解释已有结果层事实。",
    ]

    rule_hits = get_rule_hits(db=db, audit_result=audit_result)
    rule_definitions = get_rule_definitions(
        db=db,
        audit_result=audit_result,
        rule_hits=rule_hits,
    )

    rule_facts = build_rule_fact(
        audit_result=audit_result,
        rule_hits=rule_hits,
    )

    evidences: list[EvidenceSchema] = []
    citations: list[CitationSchema] = []

    evidences.append(build_audit_result_evidence(audit_result))

    if not rule_hits:
        trace_notes.append("未找到 rule_hit 命中明细，无法形成完整规则命中证据链。")
        final_summary = build_final_summary(
            audit_result=audit_result,
            rule_hits=[],
            citations=[],
        )
        return ExplanationSchema(
            audit_result_id=audit_result.id,
            clean_id=audit_result.clean_id,
            anomaly_type=audit_result.anomaly_type,
            final_summary=final_summary,
            rule_facts=rule_facts,
            evidences=dedup_evidences(evidences),
            citations=[],
            trace_notes=trace_notes,
        )

    for hit in rule_hits:
        evidences.append(build_rule_hit_evidence(hit))

    if not rule_definitions:
        trace_notes.append("未找到 rule_definition，无法确认规则定义和阈值配置。")
    else:
        for definition in rule_definitions:
            evidences.append(build_rule_definition_evidence(definition))

    seen_chunk_keys: set[str] = set()

    for hit in rule_hits:
        definition = find_definition_for_hit(
            rule_hit=hit,
            rule_definitions=rule_definitions,
        )

        query = build_explanation_query(
            audit_result=audit_result,
            rule_hit=hit,
            rule_definition=definition,
        )

        request = RetrievalQuery(
            query=query,
            top_k=chunk_top_k,
            retrieval_mode=retrieval_mode,
            audit_result_id=audit_result.id,
            clean_id=audit_result.clean_id,
            rule_code=hit.rule_code,
            rule_version=hit.rule_version,
            anomaly_type=hit.anomaly_type,
            include_inactive=False,
        )

        retrieval_response = search_rules(
            db=db,
            request=request,
            rerank_enabled=rerank_enabled,
        )

        trace_notes.extend(
            [
                f"rule_code={hit.rule_code} 检索到 {retrieval_response.total} 条 rule_chunk 候选。",
                *retrieval_response.trace_notes,
            ]
        )

        if not retrieval_response.results:
            trace_notes.append(
                f"rule_code={hit.rule_code} 未找到匹配 rule_chunk 文档依据。"
            )
            continue

        for idx, item in enumerate(retrieval_response.results, start=1):
            chunk_key = "|".join(
                [
                    str(item.chunk_id),
                    str(item.rule_code),
                    str(item.section_path),
                ]
            )

            if chunk_key in seen_chunk_keys:
                continue

            seen_chunk_keys.add(chunk_key)

            evidence = build_rule_chunk_evidence_from_retrieval(
                item=item,
                index=len(evidences) + idx,
            )
            evidences.append(evidence)

            citation = citation_from_evidence(
                evidence=evidence,
                citation_index=len(citations) + 1,
            )
            citations.append(citation)

    if not citations:
        trace_notes.append("未生成 citation，说明当前解释缺少可展示的规则文档引用。")

    final_summary = build_final_summary(
        audit_result=audit_result,
        rule_hits=rule_hits,
        citations=citations,
    )

    return ExplanationSchema(
        audit_result_id=audit_result.id,
        clean_id=audit_result.clean_id,
        anomaly_type=audit_result.anomaly_type,
        final_summary=final_summary,
        rule_facts=rule_facts,
        evidences=dedup_evidences(evidences),
        citations=citations,
        trace_notes=trace_notes,
    )


def explain_audit_result_simple(
        audit_result_id: int | None = None,
        clean_id: int | None = None,
        anomaly_type: str | None = None,
        retrieval_mode: RetrievalMode | str = RetrievalMode.HYBRID,
        chunk_top_k: int = 2,
        rerank_enabled: bool = False,
) -> ExplanationSchema:
    """
    简化调用入口，自动管理 Session。
    """
    db = SessionLocal()

    try:
        mode = retrieval_mode
        if not isinstance(mode, RetrievalMode):
            mode = RetrievalMode(str(mode))

        return explain_audit_result(
            db=db,
            audit_result_id=audit_result_id,
            clean_id=clean_id,
            anomaly_type=anomaly_type,
            retrieval_mode=mode,
            chunk_top_k=chunk_top_k,
            rerank_enabled=rerank_enabled,
        )

    finally:
        db.close()


def explanation_as_dict(
        audit_result_id: int | None = None,
        clean_id: int | None = None,
        anomaly_type: str | None = None,
        retrieval_mode: RetrievalMode | str = RetrievalMode.HYBRID,
        chunk_top_k: int = 2,
        rerank_enabled: bool = False,
) -> dict[str, Any]:
    """
    兼容旧工具层的 dict 返回入口。
    """
    explanation = explain_audit_result_simple(
        audit_result_id=audit_result_id,
        clean_id=clean_id,
        anomaly_type=anomaly_type,
        retrieval_mode=retrieval_mode,
        chunk_top_k=chunk_top_k,
        rerank_enabled=rerank_enabled,
    )
    return explanation.model_dump(mode="json")


def find_demo_audit_result_id(db: Session) -> int:
    """
    本地调试时，如果没有传 audit_result_id，则优先找一条具备 rule_hit 的已命中 audit_result。

    这样避免自动选到 legacy audit_result，导致只能走 fallback。
    """
    row = (
        db.query(AuditResult)
        .join(RuleHit, RuleHit.audit_result_id == AuditResult.id)
        .filter(
            AuditResult.is_hit.is_(True),
            RuleHit.is_hit.is_(True),
        )
        .order_by(AuditResult.id.asc())
        .first()
    )

    if row is None:
        raise ValueError(
            "当前数据库中没有同时具备 audit_result + rule_hit 的命中样本，"
            "无法自动演示完整解释链。请先运行 4号窗口规则引擎，生成 rule_hit。"
        )

    return row.id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="5号窗口：规则解释服务调试脚本")

    parser.add_argument("--audit-result-id", type=int, default=None, help="audit_result.id")
    parser.add_argument("--clean-id", type=int, default=None, help="product_clean.id")
    parser.add_argument("--anomaly-type", type=str, default=None, help="low_price / cross_platform_gap / spec_risk")
    parser.add_argument(
        "--retrieval-mode",
        type=str,
        default=RetrievalMode.HYBRID.value,
        choices=[item.value for item in RetrievalMode],
        help="baseline / vector / hybrid",
    )
    parser.add_argument("--chunk-top-k", type=int, default=2, help="每条 rule_hit 检索多少条 rule_chunk")
    parser.add_argument("--rerank", action="store_true", help="启用 rerank 预留开关")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    db = SessionLocal()

    try:
        audit_result_id = args.audit_result_id

        if audit_result_id is None and args.clean_id is None:
            audit_result_id = find_demo_audit_result_id(db)
            print(f"未传 audit_result_id，自动选择演示样本 audit_result_id={audit_result_id}")

        explanation = explain_audit_result(
            db=db,
            audit_result_id=audit_result_id,
            clean_id=args.clean_id,
            anomaly_type=args.anomaly_type,
            retrieval_mode=RetrievalMode(args.retrieval_mode),
            chunk_top_k=args.chunk_top_k,
            rerank_enabled=args.rerank,
        )

        print(
            json.dumps(
                explanation.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            )
        )

    finally:
        db.close()
