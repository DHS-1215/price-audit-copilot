# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 22:11
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session
import pandas as pd

from app.models.audit_result import AuditResult
from app.models.rule_hit import RuleHit
from app.services.audit_service import AuditService

DATABASE_URL = "mysql+pymysql://root:123456@127.0.0.1:3306/price_audit_db"


def main() -> None:
    engine = create_engine(DATABASE_URL)

    # 直接从已有 product_clean 取一小批数据，避免手写 fake clean_id 触发外键问题
    sample_df = pd.read_sql(
        """
        SELECT *
        FROM product_clean
        ORDER BY id
        LIMIT 20
        """,
        con=engine,
    )

    print("product_clean 原始列名：", sample_df.columns.tolist())

    # 1) 对齐规则引擎需要的标准列名
    rename_map = {
        "id": "clean_id",
        "standardized_brand": "normalized_brand",
        "clean_price": "price",
        "clean_platform": "normalized_platform",
    }
    sample_df = sample_df.rename(
        columns={k: v for k, v in rename_map.items() if k in sample_df.columns}
    )

    # 2) 必要字段兜底
    if "clean_id" not in sample_df.columns and "id" in sample_df.columns:
        sample_df["clean_id"] = sample_df["id"]

    if "price" not in sample_df.columns and "clean_price" in sample_df.columns:
        sample_df["price"] = sample_df["clean_price"]

    if "normalized_platform" not in sample_df.columns and "clean_platform" in sample_df.columns:
        sample_df["normalized_platform"] = sample_df["clean_platform"]

    if "normalized_brand" not in sample_df.columns and "standardized_brand" in sample_df.columns:
        sample_df["normalized_brand"] = sample_df["standardized_brand"]

    # 3) 规格风险相关辅助列兜底
    if "title_spec_hint" not in sample_df.columns:
        sample_df["title_spec_hint"] = ""

    if "title_spec_mismatch_flag" not in sample_df.columns:
        sample_df["title_spec_mismatch_flag"] = False

    if "missing_normalized_spec_flag" not in sample_df.columns:
        sample_df["missing_normalized_spec_flag"] = (
            sample_df["normalized_spec"].fillna("").astype(str).str.strip().eq("")
            if "normalized_spec" in sample_df.columns
            else True
        )

    # 4) 再看一眼现在喂给规则引擎的列
    print("对齐后列名：", sample_df.columns.tolist())

    if sample_df.empty:
        print("product_clean 表为空，无法执行 audit_service 烟雾测试。")
        return

    clean_ids = sample_df["clean_id"].tolist()

    with Session(engine) as db:
        # 为了避免重复跑时同一批 clean_id 一直堆结果，先删旧测试结果
        db.execute(delete(RuleHit).where(RuleHit.clean_id.in_(clean_ids)))
        db.execute(delete(AuditResult).where(AuditResult.clean_id.in_(clean_ids)))
        db.commit()

        service = AuditService(db)
        result = service.run_audit(
            normalized_df=sample_df,
            persist_all_results=True,
            auto_commit=True,
        )

        print("=" * 80)
        print("AuditService 返回：")
        print(result)

        print("=" * 80)
        print("audit_result 写入情况：")
        audit_rows = list(
            db.scalars(
                select(AuditResult)
                .where(AuditResult.clean_id.in_(clean_ids))
                .order_by(AuditResult.clean_id.asc(), AuditResult.anomaly_type.asc())
            ).all()
        )
        print(f"audit_result 条数: {len(audit_rows)}")
        for row in audit_rows[:10]:
            print(
                f"clean_id={row.clean_id}, "
                f"anomaly_type={row.anomaly_type}, "
                f"is_hit={row.is_hit}, "
                f"hit_rule_code={row.hit_rule_code}, "
                f"reason={row.reason_text}"
            )

        print("=" * 80)
        print("rule_hit 写入情况：")
        rule_hit_rows = list(
            db.scalars(
                select(RuleHit)
                .where(RuleHit.clean_id.in_(clean_ids))
                .order_by(RuleHit.clean_id.asc(), RuleHit.anomaly_type.asc(), RuleHit.hit_order.asc())
            ).all()
        )
        print(f"rule_hit 条数: {len(rule_hit_rows)}")
        for row in rule_hit_rows[:20]:
            print(
                f"clean_id={row.clean_id}, "
                f"anomaly_type={row.anomaly_type}, "
                f"rule_code={row.rule_code}, "
                f"is_hit={row.is_hit}, "
                f"hit_order={row.hit_order}, "
                f"message={row.hit_message}"
            )


if __name__ == "__main__":
    main()
