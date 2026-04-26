# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/24 22:59
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
给 5号窗口补一条真实 SPEC_RISK 正向命中样本。

目标：
1. 插入一条 product_clean 测试样本
2. 通过 AuditService 正常生成 audit_result / rule_hit
3. 输出 spec_risk 命中的 audit_result_id，供 5号窗口解释链测试使用
"""

from sqlalchemy import create_engine, text, select, delete
from sqlalchemy.orm import Session
import pandas as pd

from app.models.audit_result import AuditResult
from app.models.rule_hit import RuleHit
from app.services.audit_service import AuditService


DATABASE_URL = "mysql+pymysql://root:123456@127.0.0.1:3306/price_audit_db"

TEST_MARK = "SPEC_RISK_POSITIVE_FOR_WINDOW5"


def main() -> None:
    engine = create_engine(DATABASE_URL)

    with Session(engine) as db:
        # 1. 清理历史同名测试样本，避免重复跑时数据混乱
        old_clean_ids = [
            row[0]
            for row in db.execute(
                text(
                    """
                    SELECT id
                    FROM product_clean
                    WHERE normalize_note = :mark
                    """
                ),
                {"mark": TEST_MARK},
            ).all()
        ]

        if old_clean_ids:
            db.execute(delete(RuleHit).where(RuleHit.clean_id.in_(old_clean_ids)))
            db.execute(delete(AuditResult).where(AuditResult.clean_id.in_(old_clean_ids)))
            db.execute(
                text(
                    """
                    DELETE FROM product_clean
                    WHERE id IN :ids
                    """
                ).bindparams(ids=tuple(old_clean_ids))
            )
            db.commit()

        existing_raw_id = db.execute(
            text("SELECT id FROM product_raw ORDER BY id LIMIT 1")
        ).scalar()

        if existing_raw_id is None:
            raise RuntimeError("product_raw 表为空，无法创建 product_clean 测试样本")

        # 2. 插入一条真实 product_clean 样本
        # 场景：规格列是 250ml，但标题中识别出 500ml
        # 这会触发 title_spec_mismatch_flag = True
        insert_result = db.execute(
            text(
                """
                INSERT INTO product_clean (
                    raw_id,
                    standardized_brand,
                    normalized_spec,
                    clean_platform,
                    clean_price,
                    clean_title,
                    clean_spec,
                    normalize_note,
                    product_name_normalized,
                    package_quantity,
                    package_unit,
                    spec_parse_status,
                    clean_version
                )
                VALUES (
                    :raw_id,
                    :standardized_brand,
                    :normalized_spec,
                    :clean_platform,
                    :clean_price,
                    :clean_title,
                    :clean_spec,
                    :normalize_note,
                    :product_name_normalized,
                    :package_quantity,
                    :package_unit,
                    :spec_parse_status,
                    :clean_version
                )
                """
            ),
            {
                "raw_id": existing_raw_id,
                "standardized_brand": "鸿茅",
                "normalized_spec": "250ml",
                "clean_platform": "京东",
                "clean_price": 199.0,
                "clean_title": "鸿茅药酒 标题写500ml 但规格列为250ml",
                "clean_spec": "250ml",
                "normalize_note": TEST_MARK,
                "product_name_normalized": "鸿茅药酒",
                "package_quantity": 1,
                "package_unit": "瓶",
                "spec_parse_status": "title_spec_mismatch",
                "clean_version": "spec_risk_positive_v1",
            },
        )

        clean_id = insert_result.lastrowid

        # 3. 构造规则引擎需要的 DataFrame
        # 这里关键是显式带出 title_spec_hint / title_spec_mismatch_flag
        sample_df = pd.DataFrame(
            [
                {
                    "clean_id": clean_id,
                    "normalized_brand": "鸿茅",
                    "normalized_spec": "250ml",
                    "price": 199.0,
                    "normalized_platform": "京东",
                    "clean_title": "鸿茅药酒 标题写500ml 但规格列为250ml",
                    "clean_spec": "250ml",
                    "title_spec_hint": "500ml",
                    "title_spec_mismatch_flag": True,
                    "missing_normalized_spec_flag": False,
                }
            ]
        )

        # 4. 通过正式 AuditService 生成 audit_result + rule_hit
        service = AuditService(db)
        result = service.run_audit(
            normalized_df=sample_df,
            persist_all_results=True,
            auto_commit=True,
        )

        # 5. 查出 SPEC_RISK 正向命中的 audit_result
        spec_result = db.scalars(
            select(AuditResult)
            .where(AuditResult.clean_id == clean_id)
            .where(AuditResult.anomaly_type == "spec_risk")
            .where(AuditResult.is_hit.is_(True))
            .order_by(AuditResult.id.desc())
        ).first()

        if spec_result is None:
            raise RuntimeError("SPEC_RISK 正向样本生成失败：未找到 is_hit=1 的 audit_result")

        spec_rule_hit = db.scalars(
            select(RuleHit)
            .where(RuleHit.audit_result_id == spec_result.id)
            .where(RuleHit.rule_code == "SPEC_RISK")
            .where(RuleHit.is_hit.is_(True))
        ).first()

        if spec_rule_hit is None:
            raise RuntimeError("SPEC_RISK 正向样本生成失败：未找到 is_hit=1 的 rule_hit")

        print("=" * 100)
        print("SPEC_RISK 正向样本生成成功")
        print(f"clean_id: {clean_id}")
        print(f"audit_result_id: {spec_result.id}")
        print(f"anomaly_type: {spec_result.anomaly_type}")
        print(f"is_hit: {spec_result.is_hit}")
        print(f"hit_rule_code: {spec_result.hit_rule_code}")
        print(f"hit_rule_version: {spec_result.hit_rule_version}")
        print(f"reason_text: {spec_result.reason_text}")
        print("-" * 100)
        print(f"rule_hit_id: {spec_rule_hit.id}")
        print(f"rule_code: {spec_rule_hit.rule_code}")
        print(f"rule_version: {spec_rule_hit.rule_version}")
        print(f"rule_hit.is_hit: {spec_rule_hit.is_hit}")
        print(f"hit_message: {spec_rule_hit.hit_message}")
        print(f"input_snapshot_json: {spec_rule_hit.input_snapshot_json}")
        print(f"computed_value_json: {spec_rule_hit.computed_value_json}")
        print(f"threshold_snapshot_json: {spec_rule_hit.threshold_snapshot_json}")
        print("-" * 100)
        print("AuditService 返回：")
        print(result)
        print("=" * 100)
        print("5号窗口可执行：")
        print(
            f"python -m app.rag.rule_explanation_service "
            f"--audit-result-id {spec_result.id}"
        )


if __name__ == "__main__":
    main()