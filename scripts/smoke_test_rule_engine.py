# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 22:04
IDE       :PyCharm
作者      :董宏升

service 层烟雾测试
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.rule_definition import RuleDefinition
from app.services.rule_engine_service import RuleEngineService


def main() -> None:
    engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/price_audit_db")

    # 这里只做最小样本，不走全量数据
    sample_df = pd.DataFrame(
        [
            {
                "clean_id": 101,
                "clean_title": "鸿茅药酒 500ml 单瓶装",
                "clean_spec": "500ml",
                "normalized_brand": "鸿茅",
                "normalized_spec": "500ml",
                "price": 169.0,
                "normalized_platform": "京东",
                "title_spec_hint": "500ml",
                "title_spec_mismatch_flag": False,
                "missing_normalized_spec_flag": False,
            },
            {
                "clean_id": 102,
                "clean_title": "鸿茅药酒 500ml 单瓶装",
                "clean_spec": "500ml",
                "normalized_brand": "鸿茅",
                "normalized_spec": "500ml",
                "price": 260.0,
                "normalized_platform": "淘宝",
                "title_spec_hint": "500ml",
                "title_spec_mismatch_flag": False,
                "missing_normalized_spec_flag": False,
            },
            {
                "clean_id": 103,
                "clean_title": "鸿茅药酒 500ml 单瓶装",
                "clean_spec": "500ml",
                "normalized_brand": "鸿茅",
                "normalized_spec": "500ml",
                "price": 250.0,
                "normalized_platform": "拼多多",
                "title_spec_hint": "500ml",
                "title_spec_mismatch_flag": False,
                "missing_normalized_spec_flag": False,
            },
            {
                "clean_id": 104,
                "clean_title": "某商品 标题写500ml",
                "clean_spec": "250ml",
                "normalized_brand": "鸿茅",
                "normalized_spec": "250ml",
                "price": 199.0,
                "normalized_platform": "京东",
                "title_spec_hint": "500ml",
                "title_spec_mismatch_flag": True,
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

    print(f"草稿数量: {len(drafts)}")
    for draft in drafts:
        print("=" * 80)
        print(
            f"clean_id={draft.clean_id}, "
            f"anomaly_type={draft.anomaly_type}, "
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
