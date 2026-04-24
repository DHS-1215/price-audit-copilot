# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/24 22:08
IDE       :PyCharm
作者      :董宏升

5号窗口：rerank 预留适配器

当前阶段不接真实 rerank 模型，只做接口预留。

设计目的：
1. retrieval_service 可以统一保留 rerank_enabled 开关；
2. 当前默认 NoopReranker，不改变排序；
3. 后续如果接 bge-reranker / cross-encoder / LLM rerank，只需要替换本模块；
4. 不影响 baseline / vector / hybrid 主链稳定性。

当前原则：
- rerank 默认关闭；
- rerank 关闭时不改变结果顺序；
- rerank 只做排序增强，不重新定义规则事实；
- explanation 场景仍必须服从：
  audit_result -> rule_hit -> rule_definition -> rule_chunk
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from dataclasses import dataclass
from typing import Protocol

from app.rag.schemas import RetrievalResult


@dataclass(slots=True)
class RerankConfig:
    """rerank 配置。"""

    enabled: bool = False
    strategy: str = "noop"
    top_k: int | None = None


class BaseReranker(Protocol):
    """reranker 协议。"""

    def rerank(
            self,
            query: str,
            results: list[RetrievalResult],
            config: RerankConfig,
    ) -> list[RetrievalResult]:
        """对检索结果进行重排。"""
        ...


class NoopReranker:
    """
    空 reranker。

    当前阶段用于占位：
    - 不改变排序；
    - 不改变分数；
    - 只追加 score_reason，说明 rerank 当前关闭或未接真实模型。
    """

    def rerank(
            self,
            query: str,
            results: list[RetrievalResult],
            config: RerankConfig,
    ) -> list[RetrievalResult]:
        reason = "rerank_disabled"

        if config.enabled:
            reason = "rerank_enabled_but_noop_strategy"

        reranked: list[RetrievalResult] = []

        for item in results:
            score_reasons = list(item.score_reasons)

            if reason not in score_reasons:
                score_reasons.append(reason)

            reranked.append(
                item.model_copy(
                    update={
                        "rerank_score": item.rerank_score,
                        "final_score": item.final_score,
                        "score_reasons": score_reasons,
                    }
                )
            )

        if config.top_k is not None:
            return reranked[: config.top_k]

        return reranked


def get_reranker(config: RerankConfig | None = None) -> BaseReranker:
    """
    获取 reranker。

    当前只返回 NoopReranker。
    后续扩展真实 rerank 模型时，在这里根据 config.strategy 分发。
    """
    return NoopReranker()


def rerank_results(
        query: str,
        results: list[RetrievalResult],
        config: RerankConfig | None = None,
) -> list[RetrievalResult]:
    """
    rerank 对外统一入口。

    当前阶段：
    - enabled=False：不改变排序，只标记 rerank_disabled；
    - enabled=True：仍走 noop，占位真实 reranker。
    """
    config = config or RerankConfig(enabled=False)

    reranker = get_reranker(config)
    return reranker.rerank(
        query=query,
        results=results,
        config=config,
    )
