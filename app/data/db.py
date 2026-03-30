# -*- coding: utf-8 -*-
"""
创建时间    :2026/03/30 20:44
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from pathlib import Path
from typing import Optional, Union

import pandas as pd
import sqlite3

"""
因为这个第二周阶段的目标是先把数据清洗、规格归一和异常分析结果稳定持久化下来，支撑后续查询和问答能力。
项目当前是本地单人开发、数据量不大，所以我优先用了零部署、成本低、足够支撑原型验证的 SQLite，而不是一开始就把精力放到更重的数据库运维和配置上。
"""


# -------------------------
# 1. 基础路径配置
# -------------------------

def get_project_root() -> Path:
    """
    获取项目根目录：
    price-audit-copilot/
    """
    return Path(__file__).resolve().parents[2]


def get_default_db_path() -> Path:
    """
    默认 SQLite 数据库路径。
    """
    project_root = get_project_root()
    return project_root / "data" / "price_audit.db"


# -------------------------
# 2. 基础读写
# -------------------------

def load_csv(csv_path: Union[str, Path]) -> pd.DataFrame:
    """
    读取 CSV 文件，兼容常见中文编码。
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"未找到文件：{csv_path}")

    encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030"]
    last_error = None

    for enc in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=enc)
            df.columns = [str(col).replace("\ufeff", "").strip() for col in df.columns]
            return df
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"CSV 读取失败：{csv_path}\n最后错误：{last_error}")


def get_connection(db_path: Union[str, Path]) -> sqlite3.Connection:
    """
    获取 SQLite 连接。
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


# -------------------------
# 3. 表结构与落库
# -------------------------

def create_metadata_table(conn: sqlite3.Connection) -> None:
    """
    建一个轻量元数据表，记录每次落库信息。
    """
    sql = """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        row_count INTEGER NOT NULL,
        source_file TEXT,
        loaded_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """
    conn.execute(sql)
    conn.commit()


def write_dataframe_to_sql(
        df: pd.DataFrame,
        table_name: str,
        conn: sqlite3.Connection,
        source_file: Optional[str] = None,
        if_exists: str = "replace",
) -> None:
    """
    将 DataFrame 写入 SQLite。
    默认 replace，适合你当前阶段反复覆盖调试。
    """
    if df is None or df.empty:
        raise ValueError(f"表 {table_name} 写入失败：DataFrame 为空。")

    df.to_sql(table_name, conn, if_exists=if_exists, index=False)

    create_metadata_table(conn)
    conn.execute(
        """
        INSERT INTO pipeline_runs (table_name, row_count, source_file)
        VALUES (?, ?, ?)
        """,
        (table_name, int(len(df)), source_file),
    )
    conn.commit()


def load_stage_csvs_to_db(
        db_path: Union[str, Path],
        cleaned_csv_path: Union[str, Path],
        normalized_csv_path: Union[str, Path],
        anomaly_csv_path: Union[str, Path],
) -> None:
    """
    将第二周三份阶段结果文件写入数据库。
    """
    cleaned_df = load_csv(cleaned_csv_path)
    normalized_df = load_csv(normalized_csv_path)
    anomaly_df = load_csv(anomaly_csv_path)

    conn = get_connection(db_path)
    try:
        write_dataframe_to_sql(
            cleaned_df,
            table_name="cleaned_products",
            conn=conn,
            source_file=str(cleaned_csv_path),
            if_exists="replace",
        )
        write_dataframe_to_sql(
            normalized_df,
            table_name="normalized_products",
            conn=conn,
            source_file=str(normalized_csv_path),
            if_exists="replace",
        )
        write_dataframe_to_sql(
            anomaly_df,
            table_name="anomaly_details",
            conn=conn,
            source_file=str(anomaly_csv_path),
            if_exists="replace",
        )
    finally:
        conn.close()


# -------------------------
# 4. 查询辅助
# -------------------------

def list_tables(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    查看当前数据库有哪些表。
    """
    sql = """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name;
    """
    return pd.read_sql_query(sql, conn)


def preview_table(conn: sqlite3.Connection, table_name: str, limit: int = 5) -> pd.DataFrame:
    """
    预览指定表前几行。
    """
    sql = f'SELECT * FROM "{table_name}" LIMIT {int(limit)}'
    return pd.read_sql_query(sql, conn)


def get_table_row_count(conn: sqlite3.Connection, table_name: str) -> int:
    """
    获取表行数。
    """
    sql = f'SELECT COUNT(*) AS cnt FROM "{table_name}"'
    df = pd.read_sql_query(sql, conn)
    return int(df.loc[0, "cnt"])


def query_low_price_items(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    查低价异常明细。
    兼容你当前中文字段命名。
    """
    sql = """
    SELECT
        "标准化品牌",
        "规范化规格",
        "干净平台",
        "干净价格",
        "显式低价阈值",
        "组内均价",
        "当前价格/组均价比",
        "低价规则来源",
        "异常原因"
    FROM anomaly_details
    WHERE "是否疑似异常低价" = 1
    ORDER BY "标准化品牌", "规范化规格", "干净价格";
    """
    return pd.read_sql_query(sql, conn)


def query_spec_risk_items(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    查规格识别风险明细。
    """
    sql = """
    SELECT
        "标准化品牌",
        "干净标题",
        "干净规格",
        "标题规范提示",
        "规范化规格",
        "异常原因"
    FROM anomaly_details
    WHERE "是否规格识别风险" = 1
    ORDER BY "标准化品牌", "干净标题";
    """
    return pd.read_sql_query(sql, conn)


def query_low_price_by_platform(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    查哪个平台低价最多。
    """
    sql = """
    SELECT
        "干净平台" AS 平台,
        COUNT(*) AS 低价数量
    FROM anomaly_details
    WHERE "是否疑似异常低价" = 1
    GROUP BY "干净平台"
    ORDER BY 低价数量 DESC, 平台 ASC;
    """
    return pd.read_sql_query(sql, conn)


def query_max_price_gap_by_brand(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    查哪个品牌跨平台价差最大。
    直接从 anomaly_details 表按品牌+规格聚合。
    """
    sql = """
    WITH group_gap AS (
        SELECT
            "标准化品牌" AS 品牌,
            "规范化规格" AS 规格,
            MAX("干净价格") AS 最高价,
            MIN("干净价格") AS 最低价
        FROM anomaly_details
        GROUP BY "标准化品牌", "规范化规格"
    ),
    brand_gap AS (
        SELECT
            品牌,
            规格,
            最高价,
            最低价,
            (最高价 - 最低价) AS 价差金额,
            CASE
                WHEN 最高价 IS NOT NULL AND 最高价 != 0
                THEN (最高价 - 最低价) * 1.0 / 最高价
                ELSE NULL
            END AS 价差比例
        FROM group_gap
    )
    SELECT *
    FROM brand_gap
    ORDER BY 价差金额 DESC, 品牌 ASC;
    """
    return pd.read_sql_query(sql, conn)


# -------------------------
# 5. 本地调试入口
# -------------------------

if __name__ == "__main__":
    project_root = get_project_root()

    db_path = project_root / "data" / "price_audit.db"
    cleaned_csv_path = project_root / "data" / "cleaned_products_preview.csv"
    normalized_csv_path = project_root / "data" / "normalized_products_preview.csv"
    anomaly_csv_path = project_root / "data" / "异常明细.csv"

    print("开始写入 SQLite 数据库...")
    print("数据库路径：", db_path)

    load_stage_csvs_to_db(
        db_path=db_path,
        cleaned_csv_path=cleaned_csv_path,
        normalized_csv_path=normalized_csv_path,
        anomaly_csv_path=anomaly_csv_path,
    )

    conn = get_connection(db_path)
    try:
        print("\n当前数据库中的表：")
        print(list_tables(conn))

        for table_name in ["cleaned_products", "normalized_products", "anomaly_details"]:
            print(f"\n表 {table_name} 行数：{get_table_row_count(conn, table_name)}")

        print("\n低价异常预览：")
        print(query_low_price_items(conn).head())

        print("\n规格风险预览：")
        print(query_spec_risk_items(conn).head())

        print("\n哪个平台低价最多：")
        print(query_low_price_by_platform(conn))

        print("\n哪个品牌跨平台价差最大：")
        print(query_max_price_gap_by_brand(conn).head())
    finally:
        conn.close()
