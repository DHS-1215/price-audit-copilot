# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/21 12:29
IDE       :PyCharm
作者      :董宏升

5号窗口：RAG 检索与规则解释 Schema

本模块用于统一 5号窗口的 RAG 输出结构，避免 retrieval / explanation / citation
各自返回散乱 dict，导致后续 6号窗口 /ask 编排层难以复用。

核心原则：
1. retrieval result 负责承接检索结果；
2. evidence 负责承接系统内部证据；
3. citation 负责承接对外展示引用；
4. explanation 负责承接异常解释结果；
5. explanation 必须服从：
   audit_result -> rule_hit -> rule_definition -> rule_chunk
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RetrievalMode(str, Enum):
    """检索模式。"""

    BASELINE = "baseline"
    VECTOR = "vector"
    HYBRID = "hybrid"


class EvidenceType(str, Enum):
    """证据类型。"""

    AUDIT_RESULT = "audit_result"
    RULE_HIT = "rule_hit"
    RULE_DEFINITION = "rule_definition"
    RULE_CHUNK = "rule_chunk"
    RETRIEVAL_RESULT = "retrieval_result"
    MANUAL_REVIEW = "manual_review"


class ChunkType(str, Enum):
    """规则文档 chunk 类型。"""

    RULE_TEXT = "rule_text"
    DEFINITION = "definition"
    THRESHOLD = "threshold"
    EXAMPLE = "example"
    MANUAL_REVIEW = "manual_review"
    FAQ = "faq"
    NOTE = "note"


class RetrievalQuery(BaseModel):
    """
    规则检索请求。

    既支持普通 retrieval 场景，也支持 explanation 场景下带规则约束的检索。
    """

    query: str | None = Field(
        default=None,
        description="用户查询文本，retrieval 场景常用",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="返回候选数量",
    )
    retrieval_mode: RetrievalMode = Field(
        default=RetrievalMode.BASELINE,
        description="检索模式：baseline / vector / hybrid",
    )

    # explanation 场景常用约束
    audit_result_id: int | None = Field(
        default=None,
        description="异常结果 ID，explanation 场景使用",
    )
    clean_id: int | None = Field(
        default=None,
        description="清洗后商品 ID，explanation 场景可用",
    )
    rule_code: str | None = Field(
        default=None,
        description="规则编码，如 LOW_PRICE_EXPLICIT / SPEC_RISK",
    )
    rule_version: str | None = Field(
        default=None,
        description="规则版本",
    )
    anomaly_type: str | None = Field(
        default=None,
        description="异常类型：low_price / cross_platform_gap / spec_risk",
    )

    include_inactive: bool = Field(
        default=False,
        description="是否包含未启用 rule_chunk，默认不包含",
    )


class RetrievalResult(BaseModel):
    """
    单条检索结果。

    baseline / vector / hybrid 最终都应统一转换成这个结构。
    """

    model_config = ConfigDict(from_attributes=True)

    chunk_id: int | str | None = Field(default=None, description="命中的 rule_chunk.id 或向量索引中的 chunk 标识")
    rule_definition_id: int | None = Field(
        default=None,
        description="关联的 rule_definition.id",
    )

    rule_code: str | None = Field(default=None, description="规则编码")
    rule_version: str | None = Field(default=None, description="规则版本")
    anomaly_type: str | None = Field(default=None, description="异常类型")

    doc_name: str | None = Field(default=None, description="文档文件名或旧版文档名")
    doc_title: str | None = Field(default=None, description="文档标题")
    source_doc_path: str | None = Field(default=None, description="来源规则文档路径")

    section_title: str | None = Field(default=None, description="章节标题")
    section_path: str | None = Field(default=None, description="完整章节路径")

    chunk_index: int | None = Field(default=None, description="chunk 序号")
    chunk_text: str | None = Field(default=None, description="chunk 正文")
    preview_text: str | None = Field(default=None, description="展示预览文本")
    chunk_type: str | None = Field(default=None, description="chunk 类型")

    metadata: dict[str, Any] | None = Field(
        default=None,
        description="检索 metadata",
    )

    baseline_score: float | None = Field(default=None, description="baseline 分数")
    vector_score: float | None = Field(default=None, description="向量检索分数")
    fusion_score: float | None = Field(default=None, description="混合检索融合分数")
    rerank_score: float | None = Field(default=None, description="rerank 分数")
    final_score: float | None = Field(default=None, description="最终排序分数")

    score_reasons: list[str] = Field(
        default_factory=list,
        description="命中原因，如 rule_code_exact_match / anomaly_type_match",
    )
    retrieval_mode: RetrievalMode = Field(
        default=RetrievalMode.BASELINE,
        description="本条结果来自哪种检索模式",
    )


class RetrievalResponse(BaseModel):
    """规则检索响应。"""

    query: str | None = Field(default=None, description="原始查询")
    retrieval_mode: RetrievalMode = Field(
        default=RetrievalMode.BASELINE,
        description="检索模式",
    )
    top_k: int = Field(default=5, description="请求 top_k")
    results: list[RetrievalResult] = Field(
        default_factory=list,
        description="检索结果列表",
    )
    total: int = Field(default=0, description="返回结果数量")
    trace_notes: list[str] = Field(
        default_factory=list,
        description="检索过程说明或降级说明",
    )


class EvidenceSchema(BaseModel):
    """
    系统内部证据对象。

    evidence 用于 service / orchestration / test / trace，不等同于对外展示引用。
    """

    evidence_id: str = Field(description="证据 ID")
    evidence_type: EvidenceType = Field(description="证据类型")
    source_table: str = Field(description="来源表或来源对象")
    source_id: int | str | None = Field(default=None, description="来源对象 ID")

    rule_code: str | None = Field(default=None, description="规则编码")
    rule_version: str | None = Field(default=None, description="规则版本")
    anomaly_type: str | None = Field(default=None, description="异常类型")

    doc_title: str | None = Field(default=None, description="文档标题")
    section_title: str | None = Field(default=None, description="章节标题")
    section_path: str | None = Field(default=None, description="章节路径")
    chunk_id: int | str | None = Field(default=None, description="rule_chunk ID")
    source_doc_path: str | None = Field(default=None, description="来源文档路径")

    preview_text: str | None = Field(default=None, description="证据预览文本")

    score: float | None = Field(default=None, description="证据分数")
    score_reasons: list[str] = Field(
        default_factory=list,
        description="证据被选中的原因",
    )

    metadata: dict[str, Any] | None = Field(default=None, description="metadata")

    input_snapshot: dict[str, Any] | None = Field(
        default=None,
        description="输入快照，通常来自 rule_hit.input_snapshot_json",
    )
    threshold_snapshot: dict[str, Any] | None = Field(
        default=None,
        description="阈值快照，通常来自 rule_hit.threshold_snapshot_json",
    )
    computed_value: dict[str, Any] | None = Field(
        default=None,
        description="计算值，通常来自 rule_hit.computed_value_json",
    )

    trace_note: str | None = Field(default=None, description="证据追踪说明")


class CitationSchema(BaseModel):
    """
    对外展示引用对象。

    citation 通常由 rule_chunk 类型 evidence 转换而来。
    它用于 /ask、UI、报告展示，不承载完整内部证据链。
    """

    citation_id: str = Field(description="引用 ID，如 CIT-001")
    evidence_id: str | None = Field(default=None, description="对应 evidence ID")

    doc_title: str | None = Field(default=None, description="文档标题")
    section_title: str | None = Field(default=None, description="章节标题")
    section_path: str | None = Field(default=None, description="章节路径")
    chunk_id: int | str | None = Field(default=None, description="rule_chunk ID")
    source_doc_path: str | None = Field(default=None, description="来源文档路径")

    quoted_preview: str | None = Field(default=None, description="引用预览")
    citation_note: str | None = Field(default=None, description="引用说明")

    rule_code: str | None = Field(default=None, description="规则编码")
    rule_version: str | None = Field(default=None, description="规则版本")
    anomaly_type: str | None = Field(default=None, description="异常类型")


class RuleFactSchema(BaseModel):
    """
    规则事实摘要。

    用于 explanation 输出中总结 4号窗口已经确定的结果层事实。
    """

    audit_result_id: int | None = Field(default=None, description="异常结果 ID")
    clean_id: int | None = Field(default=None, description="清洗后商品 ID")
    anomaly_type: str | None = Field(default=None, description="异常类型")

    is_hit: bool | None = Field(default=None, description="是否命中异常")
    hit_rule_code: str | None = Field(default=None, description="主命中规则编码")
    hit_rule_version: str | None = Field(default=None, description="主命中规则版本")

    reason_text: str | None = Field(default=None, description="结果摘要原因")
    hit_messages: list[str] = Field(
        default_factory=list,
        description="rule_hit 命中消息列表",
    )

    input_snapshot: dict[str, Any] | None = Field(default=None, description="输入快照")
    threshold_snapshot: dict[str, Any] | None = Field(default=None, description="阈值快照")
    computed_value: dict[str, Any] | None = Field(default=None, description="计算值")


class ExplanationSchema(BaseModel):
    """
    异常解释结果。

    explanation 必须遵守：
    audit_result -> rule_hit -> rule_definition -> rule_chunk
    """

    audit_result_id: int | None = Field(default=None, description="异常结果 ID")
    clean_id: int | None = Field(default=None, description="清洗后商品 ID")
    anomaly_type: str | None = Field(default=None, description="异常类型")

    final_summary: str = Field(default="", description="最终解释摘要")
    rule_facts: RuleFactSchema | None = Field(default=None, description="结果层事实摘要")

    evidences: list[EvidenceSchema] = Field(
        default_factory=list,
        description="内部证据链",
    )
    citations: list[CitationSchema] = Field(
        default_factory=list,
        description="对外展示引用",
    )

    trace_notes: list[str] = Field(
        default_factory=list,
        description="解释过程说明、降级说明、版本不一致说明等",
    )


class RuleChunkDraft(BaseModel):
    """
    rule_chunk 构建草稿。

    ingest_service / chunk builder 可以先生成这个结构，再写入数据库。
    """

    rule_definition_id: int | None = Field(default=None, description="关联规则定义 ID")

    rule_code: str | None = Field(default=None, description="规则编码")
    rule_version: str | None = Field(default=None, description="规则版本")
    anomaly_type: str | None = Field(default=None, description="异常类型")

    doc_name: str = Field(description="文档文件名")
    doc_title: str | None = Field(default=None, description="文档标题")
    source_doc_path: str | None = Field(default=None, description="来源文档路径")

    section_title: str | None = Field(default=None, description="章节标题")
    section_path: str | None = Field(default=None, description="章节路径")

    chunk_index: int = Field(description="chunk 序号")
    chunk_text: str = Field(description="chunk 正文")
    chunk_type: str | None = Field(default=None, description="chunk 类型")

    keywords_json: list[str] | None = Field(default=None, description="关键词列表")
    metadata_json: dict[str, Any] | None = Field(default=None, description="metadata")

    embedding_ref: str | None = Field(default=None, description="向量索引引用标识")
    is_active: bool = Field(default=True, description="是否启用")


def build_preview_text(text: str | None, max_len: int = 160) -> str:
    """
    构建预览文本。

    避免 retrieval / evidence / citation 各自重复写截断逻辑。
    """
    if not text:
        return ""

    normalized = " ".join(str(text).split())
    if len(normalized) <= max_len:
        return normalized

    return normalized[:max_len].rstrip() + "..."


def citation_from_evidence(
        evidence: EvidenceSchema,
        citation_index: int,
) -> CitationSchema:
    """
    从 rule_chunk 类型 evidence 构建 citation。

    注意：
    citation 是展示对象，不替代 evidence。
    """
    citation_id = f"CIT-{citation_index:03d}"

    return CitationSchema(
        citation_id=citation_id,
        evidence_id=evidence.evidence_id,
        doc_title=evidence.doc_title,
        section_title=evidence.section_title,
        section_path=evidence.section_path,
        chunk_id=evidence.chunk_id,
        source_doc_path=evidence.source_doc_path,
        quoted_preview=evidence.preview_text,
        citation_note=(
            f"该依据来自 {evidence.doc_title or '规则文档'}"
            f"{' / ' + evidence.section_title if evidence.section_title else ''}。"
        ),
        rule_code=evidence.rule_code,
        rule_version=evidence.rule_version,
        anomaly_type=evidence.anomaly_type,
    )
