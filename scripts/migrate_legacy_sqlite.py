# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 11:31
IDE       :PyCharm
作者      :董宏升

将旧 SQLite 原型数据迁移到正式 MySQL 数据库。

迁移策略（最小可用版）：
1. 优先读取 data/legacy/price_audit.db
2. 优先使用 anomaly_details 作为主数据来源
3. 为每条旧记录创建：
   - 1 条 ProductRaw
   - 1 条 ProductClean
   - 0~3 条 AuditResult（按异常命中情况拆分）
4. 不在本脚本里迁移 rule_definition / rule_chunk / ask_log / model_call_log
   因为这些已经由 Alembic 结构和规则 seed 负责，旧 SQLite 也不是它们的正式来源
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！

import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models import AuditResult, ProductClean, ProductRaw


# -------------------------
# 路径与参数
# -------------------------

def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_default_legacy_db_path() -> Path:
    return get_project_root() / "data" / "legacy" / "price_audit.db"


# -------------------------
# 数据读取
# -------------------------

def read_sqlite_table(conn: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    try:
        return pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
    except Exception:
        return pd.DataFrame()


def load_legacy_tables(legacy_db_path: Path) -> dict[str, pd.DataFrame]:
    if not legacy_db_path.exists():
        raise FileNotFoundError(f"未找到旧 SQLite 数据库：{legacy_db_path}")

    conn = sqlite3.connect(str(legacy_db_path))
    try:
        return {
            "cleaned_products": read_sqlite_table(conn, "cleaned_products"),
            "normalized_products": read_sqlite_table(conn, "normalized_products"),
            "anomaly_details": read_sqlite_table(conn, "anomaly_details"),
            "pipeline_runs": read_sqlite_table(conn, "pipeline_runs"),
        }
    finally:
        conn.close()


# -------------------------
# 值转换
# -------------------------
# 统一判断空值
def is_null_like(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


# 转字符串并去空格
def normalize_str(value: Any) -> str | None:
    if is_null_like(value):
        return None
    text = str(value).strip()
    return text if text else None


# 转进制
def normalize_decimal(value: Any) -> Decimal | None:
    if is_null_like(value):
        return None
    try:
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return None


# 把 1/true/是/命中 这些都统一成布尔值
def normalize_bool(value: Any) -> bool:
    if is_null_like(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) == 1
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "是", "命中"}


# 把 Decimal、日期、dict、list 这些变成可 JSON 序列化的形式
def json_safe(value: Any) -> Any:
    if is_null_like(value):
        return None
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value


# 把整行转成 JSON 快照
def row_to_payload(row: pd.Series) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in row.to_dict().items():
        payload[str(key)] = json_safe(value)
    return payload


# 多个候选字段里，拿第一个非空值
def first_non_null(row: pd.Series, candidates: list[str]) -> Any:
    for col in candidates:
        if col in row.index:
            value = row[col]
            if not is_null_like(value):
                return value
    return None


# -------------------------
# 映射逻辑
# -------------------------

@dataclass
class ImportStats:
    product_raw_count: int = 0
    product_clean_count: int = 0
    audit_result_count: int = 0


# 从旧表一行数据，拼出一条 ProductRaw。
def build_product_raw_from_row(row: pd.Series, batch_no: str) -> ProductRaw:
    source_platform = normalize_str(
        first_non_null(row, ["干净平台", "平台", "source_platform"])
    ) or "legacy_unknown"

    source_title = normalize_str(
        first_non_null(row, ["干净标题", "商品标题", "标题", "source_product_title"])
    ) or "legacy_unknown_title"

    source_spec_text = normalize_str(
        first_non_null(row, ["干净规格", "规范化规格", "规格", "source_spec_text"])
    )

    source_price_text = normalize_str(
        first_non_null(row, ["干净价格", "价格", "source_price_text"])
    )

    source_price_value = normalize_decimal(
        first_non_null(row, ["干净价格", "价格", "source_price_value"])
    )

    return ProductRaw(
        batch_no=batch_no,
        source_platform=source_platform,
        source_shop_name=normalize_str(first_non_null(row, ["店铺", "店铺名", "source_shop_name"])),
        source_product_title=source_title,
        source_spec_text=source_spec_text,
        source_price_text=source_price_text,
        source_price_value=source_price_value,
        product_url=normalize_str(first_non_null(row, ["商品链接", "链接", "product_url"])),
        sku_id=normalize_str(first_non_null(row, ["sku_id", "SKU", "商品ID"])),
        source_payload_json=row_to_payload(row),
        ingest_source="legacy_sqlite",
    )


# 从同一行数据，再拼一条 ProductClean。
def build_product_clean_from_row(row: pd.Series, raw_id: int) -> ProductClean:
    return ProductClean(
        raw_id=raw_id,
        standardized_brand=normalize_str(first_non_null(row, ["标准化品牌", "品牌"])),
        normalized_spec=normalize_str(first_non_null(row, ["规范化规格", "规格"])),
        clean_platform=normalize_str(first_non_null(row, ["干净平台", "平台"])),
        clean_price=normalize_decimal(first_non_null(row, ["干净价格", "价格"])),
        clean_title=normalize_str(first_non_null(row, ["干净标题", "商品标题", "标题"])),
        clean_spec=normalize_str(first_non_null(row, ["干净规格", "规格"])),
        normalize_note=normalize_str(first_non_null(row, ["标题规范提示", "清洗说明"])),
        product_name_normalized=normalize_str(first_non_null(row, ["商品名", "product_name"])),
        package_quantity=normalize_decimal(first_non_null(row, ["包装数量", "package_quantity"])),
        package_unit=normalize_str(first_non_null(row, ["包装单位", "package_unit"])),
        spec_parse_status=normalize_str(
            first_non_null(row, ["规格解析状态", "spec_parse_status"])) or "legacy_imported",
        clean_version="legacy_v1",
    )


# 根据一行里的几个布尔字段判断要不要生成审核结果：
def build_audit_results_from_row(row: pd.Series, clean_id: int) -> list[AuditResult]:
    results: list[AuditResult] = []

    common_reason = normalize_str(first_non_null(row, ["异常原因"]))
    low_price_source = normalize_str(first_non_null(row, ["低价规则来源"]))

    if normalize_bool(first_non_null(row, ["是否疑似异常低价"])):
        results.append(
            AuditResult(
                clean_id=clean_id,
                anomaly_type="low_price",
                is_hit=True,
                hit_rule_code=None,  # 旧数据里先不强绑规则编码
                hit_rule_version="legacy_v1",
                explicit_low_price_threshold=normalize_decimal(first_non_null(row, ["显式低价阈值"])),
                group_avg_price=normalize_decimal(first_non_null(row, ["组内均价"])),
                price_to_group_avg_ratio=normalize_decimal(first_non_null(row, ["当前价格/组均价比"])),
                low_price_rule_source=low_price_source,
                reason_text=common_reason,
                input_snapshot_json=row_to_payload(row),
                result_status="pending_review",
            )
        )

    if normalize_bool(first_non_null(row, ["是否跨平台价差异常"])):
        results.append(
            AuditResult(
                clean_id=clean_id,
                anomaly_type="cross_platform_gap",
                is_hit=True,
                hit_rule_code="CROSS_PLATFORM_GAP",
                hit_rule_version="legacy_v1",
                reason_text=common_reason,
                input_snapshot_json=row_to_payload(row),
                result_status="pending_review",
            )
        )

    if normalize_bool(first_non_null(row, ["是否规格识别风险"])):
        results.append(
            AuditResult(
                clean_id=clean_id,
                anomaly_type="spec_risk",
                is_hit=True,
                hit_rule_code="SPEC_RISK",
                hit_rule_version="legacy_v1",
                reason_text=common_reason,
                input_snapshot_json=row_to_payload(row),
                result_status="pending_review",
            )
        )

    return results


# -------------------------
# 迁移主流程
# -------------------------
# 先连目标库，检查 product_raw、product_clean、audit_result 三张表在不在。
def ensure_required_tables(database_url: str) -> None:
    engine = create_engine(database_url, future=True)
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    required = {"product_raw", "product_clean", "audit_result"}
    missing = required - existing
    if missing:
        raise RuntimeError(
            f"目标库缺少必要表：{sorted(missing)}。"
            f"请先执行 alembic upgrade head。"
        )
    engine.dispose()


def truncate_target_tables(session: Session) -> None:
    # 按依赖逆序删除，避免 FK 冲突
    session.query(AuditResult).delete()
    session.query(ProductClean).delete()
    session.query(ProductRaw).delete()
    session.commit()


# 按优先级选主来源表
def select_primary_source_df(tables: dict[str, pd.DataFrame]) -> tuple[str, pd.DataFrame]:
    for name in ["anomaly_details", "normalized_products", "cleaned_products"]:
        df = tables.get(name, pd.DataFrame())
        if df is not None and not df.empty:
            return name, df
    return "empty", pd.DataFrame()


def migrate_legacy_sqlite(
        legacy_db_path: Path,
        database_url: str,
        truncate_target: bool = False,
        dry_run: bool = False,
) -> ImportStats:
    """
    检查目标表是否存在
    读取旧 SQLite 各张表
    选主来源表
    如果主表为空，直接报错
    打印主表信息
    如果是 dry-run，就只预览，不写库
    真正执行时，建立 SQLAlchemy Session
    每行依次：
    建 ProductRaw
    flush() 拿到 raw_id
    建 ProductClean
    flush() 拿到 clean_id
    如果主表就是 anomaly_details，再拆出 AuditResult
    最后统一 commit
    标准 ETL 思维：
    读取 → 归一 → 映射 → 入库。
    """

    ensure_required_tables(database_url)

    tables = load_legacy_tables(legacy_db_path)
    source_name, source_df = select_primary_source_df(tables)
    anomaly_df = tables.get("anomaly_details", pd.DataFrame())

    if source_df.empty:
        raise RuntimeError(
            "旧 SQLite 中未找到可导入的数据表内容。"
            "至少需要 anomaly_details / normalized_products / cleaned_products 之一。"
        )

    print(f"[INFO] 旧库路径：{legacy_db_path}")
    print(f"[INFO] 主数据来源表：{source_name}，共 {len(source_df)} 行")
    if anomaly_df is not None and not anomaly_df.empty:
        print(f"[INFO] anomaly_details 行数：{len(anomaly_df)}（可导入审核结果）")
    else:
        print("[WARN] anomaly_details 为空，本次只导入 product_raw / product_clean，不导入 audit_result")

    if dry_run:
        print("[DRY RUN] 仅预览，不写入正式库。")
        return ImportStats(
            product_raw_count=len(source_df),
            product_clean_count=len(source_df),
            audit_result_count=0 if anomaly_df.empty else -1,  # 仅表示未知/未实际统计
        )

    engine = create_engine(database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    stats = ImportStats()
    batch_no = f"legacy_import_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"

    with SessionLocal() as session:
        if truncate_target:
            print("[WARN] 即将清空目标表：audit_result / product_clean / product_raw")
            truncate_target_tables(session)

        for _, row in source_df.iterrows():
            raw_obj = build_product_raw_from_row(row, batch_no=batch_no)
            session.add(raw_obj)
            session.flush()
            stats.product_raw_count += 1

            clean_obj = build_product_clean_from_row(row, raw_id=raw_obj.id)
            session.add(clean_obj)
            session.flush()
            stats.product_clean_count += 1

            # 只有主来源本身就是 anomaly_details 时，才能稳定拿到异常命中字段
            if source_name == "anomaly_details":
                audit_rows = build_audit_results_from_row(row, clean_id=clean_obj.id)
                for audit_obj in audit_rows:
                    session.add(audit_obj)
                    stats.audit_result_count += 1

        session.commit()

    engine.dispose()
    return stats


# -------------------------
# CLI
# -------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="迁移旧 SQLite 数据到正式 MySQL 库")
    parser.add_argument(
        "--legacy-db",
        type=str,
        default=str(get_default_legacy_db_path()),
        help="旧 SQLite 数据库路径，默认 data/legacy/price_audit.db",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=os.getenv("DATABASE_URL", ""),
        help="目标数据库连接串；不传则读取环境变量 DATABASE_URL",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="迁移前清空目标表（仅清空 product_raw / product_clean / audit_result）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只预览，不实际写入",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    legacy_db_path = Path(args.legacy_db)
    database_url = args.database_url.strip()

    if not database_url:
        raise ValueError("未提供目标数据库连接串，请传 --database-url 或设置 DATABASE_URL。")

    stats = migrate_legacy_sqlite(
        legacy_db_path=legacy_db_path,
        database_url=database_url,
        truncate_target=args.truncate_target,
        dry_run=args.dry_run,
    )

    print("\n====== 迁移完成 ======")
    print(f"product_raw 导入：{stats.product_raw_count}")
    print(f"product_clean 导入：{stats.product_clean_count}")
    print(f"audit_result 导入：{stats.audit_result_count}")


if __name__ == "__main__":
    main()
