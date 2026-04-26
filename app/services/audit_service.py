# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/22 21:39
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from collections import Counter
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_result import AuditResult
from app.models.rule_definition import RuleDefinition
from app.models.rule_hit import RuleHit
from app.services.rule_engine_service import (
    AuditResultDraft,
    RuleEngineService,
)


class AuditService:
    """
    审核结果服务：
    - 读取启用中的规则定义
    - 调用规则引擎
    - 生成 audit_result
    - 生成 rule_hit
    - 持久化到数据库
    """

    def __init__(self, db: Session):
        self.db = db

    # ==========
    # 主入口
    # ==========

    def run_audit(
            self,
            normalized_df: pd.DataFrame,
            *,
            persist_all_results: bool = True,
            auto_commit: bool = True,
    ) -> dict[str, Any]:
        """
        对规范化后的数据执行审核，并落库。

        参数：
        - normalized_df: 已经完成清洗/归一化的数据 DataFrame
        - persist_all_results:
            True  -> 每个 clean_id * 每个 anomaly_type 都写一条 audit_result（命中/未命中都保留）
            False -> 仅写入命中的 audit_result
        - auto_commit:
            True  -> 服务内部 commit
            False -> 由调用方自己控制事务
        """
        rule_definitions = self.load_enabled_rule_definitions()
        engine = RuleEngineService(rule_definitions=rule_definitions)

        drafts = engine.evaluate_dataframe(normalized_df)
        persisted_results = self.persist_drafts(
            drafts=drafts,
            persist_all_results=persist_all_results,
        )

        if auto_commit:
            self.db.commit()

        summary = self.build_summary(persisted_results)
        return {
            "success": True,
            "total_audit_results": len(persisted_results),
            "summary": summary,
        }

    # ==========
    # 规则加载
    # ==========

    def load_enabled_rule_definitions(self) -> list[RuleDefinition]:
        stmt = (
            select(RuleDefinition)
            .where(RuleDefinition.enabled.is_(True))
            .order_by(RuleDefinition.rule_type.asc(), RuleDefinition.rule_code.asc())
        )
        return list(self.db.scalars(stmt).all())

    # ==========
    # 落库主流程
    # ==========

    def persist_drafts(
            self,
            drafts: list[AuditResultDraft],
            *,
            persist_all_results: bool,
    ) -> list[AuditResult]:
        """
        把规则引擎草稿持久化为：
        - audit_result
        - rule_hit
        """
        persisted_results: list[AuditResult] = []

        for draft in drafts:
            if not persist_all_results and not draft.is_hit:
                continue

            audit_result = self.create_audit_result_from_draft(draft)
            self.db.add(audit_result)
            self.db.flush()  # 拿到 audit_result.id

            rule_hits = self.create_rule_hits_from_draft(
                audit_result_id=audit_result.id,
                draft=draft,
            )
            for item in rule_hits:
                self.db.add(item)

            persisted_results.append(audit_result)

        return persisted_results

    def create_audit_result_from_draft(self, draft: AuditResultDraft) -> AuditResult:
        return AuditResult(
            clean_id=draft.clean_id,
            anomaly_type=draft.anomaly_type,
            is_hit=draft.is_hit,
            hit_rule_code=draft.hit_rule_code,
            hit_rule_version=draft.hit_rule_version,
            rule_definition_id=draft.rule_definition_id,
            explicit_low_price_threshold=draft.explicit_low_price_threshold,
            group_avg_price=draft.group_avg_price,
            price_to_group_avg_ratio=draft.price_to_group_avg_ratio,
            low_price_rule_source=draft.low_price_rule_source,
            reason_text=draft.reason_text,
            input_snapshot_json=draft.input_snapshot_json,
            result_status="pending_review",
            audited_at=datetime.utcnow(),
        )

    def create_rule_hits_from_draft(
            self,
            *,
            audit_result_id: int,
            draft: AuditResultDraft,
    ) -> list[RuleHit]:
        items: list[RuleHit] = []

        for hit in draft.rule_hits:
            items.append(
                RuleHit(
                    audit_result_id=audit_result_id,
                    clean_id=draft.clean_id,
                    anomaly_type=hit.anomaly_type,
                    rule_code=hit.rule_code,
                    rule_version=hit.rule_version,
                    rule_definition_id=hit.rule_definition_id,
                    is_hit=hit.is_hit,
                    input_snapshot_json=hit.input_snapshot_json,
                    computed_value_json=hit.computed_value_json,
                    threshold_snapshot_json=hit.threshold_snapshot_json,
                    hit_message=hit.hit_message,
                    hit_order=hit.hit_order,
                )
            )

        return items

    # ==========
    # 汇总
    # ==========

    def build_summary(self, persisted_results: list[AuditResult]) -> dict[str, Any]:
        anomaly_counter: Counter[str] = Counter()
        hit_counter: Counter[str] = Counter()

        for item in persisted_results:
            anomaly_counter[item.anomaly_type] += 1
            if item.is_hit:
                hit_counter[item.anomaly_type] += 1

        return {
            "by_anomaly_type": dict(anomaly_counter),
            "hit_by_anomaly_type": dict(hit_counter),
            "total_hits": sum(hit_counter.values()),
        }
