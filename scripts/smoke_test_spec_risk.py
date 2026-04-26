# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/23 20:31
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import pandas as pd

from app.models.rule_definition import RuleDefinition
from app.services.rule_engine_service import RuleEngineService

DATABASE_URL = "mysql+pymysql://root:123456@127.0.0.1:3306/price_audit_db"


def main() -> None:
    engine = create_engine(DATABASE_URL)

    # 专门构造能打中 spec_risk 的样本
    sample_df = pd.DataFrame(
        [
            # 1. 标题规格与规格列冲突
            {
                "clean_id": 9001,
                "clean_title": "鸿茅药酒 标题写500ml",
                "clean_spec": "250ml",
                "normalized_brand": "鸿茅",
                "normalized_spec": "250ml",
                "price": 199.0,
                "normalized_platform": "京东",
                "title_spec_hint": "500ml",
                "title_spec_mismatch_flag": True,
                "missing_normalized_spec_flag": False,
            },
            # 2. 规范化规格缺失
            {
                "clean_id": 9002,
                "clean_title": "鸿茅药酒 规格不清",
                "clean_spec": "",
                "normalized_brand": "鸿茅",
                "normalized_spec": "",
                "price": 210.0,
                "normalized_platform": "淘宝",
                "title_spec_hint": "",
                "title_spec_mismatch_flag": False,
                "missing_normalized_spec_flag": True,
            },
            # 3. 同时命中两种规格风险
            {
                "clean_id": 9003,
                "clean_title": "标题写500ml 但规格缺失",
                "clean_spec": "",
                "normalized_brand": "鸿茅",
                "normalized_spec": "",
                "price": 220.0,
                "normalized_platform": "拼多多",
                "title_spec_hint": "500ml",
                "title_spec_mismatch_flag": True,
                "missing_normalized_spec_flag": True,
            },
            # 4. 正常样本，对照组
            {
                "clean_id": 9004,
                "clean_title": "鸿茅药酒 500ml",
                "clean_spec": "500ml",
                "normalized_brand": "鸿茅",
                "normalized_spec": "500ml",
                "price": 230.0,
                "normalized_platform": "京东",
                "title_spec_hint": "500ml",
                "title_spec_mismatch_flag": False,
                "missing_normalized_spec_flag": False,
            },
        ]
    )

    with Session(engine) as db:
        rule_definitions = list(
            db.scalars(
                select(RuleDefinition)
                .where(RuleDefinition.enabled.is_(True))
                .order_by(RuleDefinition.rule_code.asc())
            ).all()
        )

        service = RuleEngineService(rule_definitions=rule_definitions)
        drafts = service.evaluate_dataframe(sample_df)

    print("=" * 80)
    print("只看 spec_risk 结果：")
    for draft in drafts:
        if draft.anomaly_type != "spec_risk":
            continue
        print(
            f"clean_id={draft.clean_id}, "
            f"is_hit={draft.is_hit}, "
            f"hit_rule_code={draft.hit_rule_code}, "
            f"reason={draft.reason_text}"
        )
        for hit in draft.rule_hits:
            print(
                f"  - rule_code={hit.rule_code}, "
                f"is_hit={hit.is_hit}, "
                f"message={hit.hit_message}"
            )


if __name__ == "__main__":
    main()
