# -*- coding: utf-8 -*-
"""
创建时间    :2026/03/29 15:32
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from pathlib import Path
from typing import Optional, Union

import pandas as pd


# -------------------------
# 1. 参数配置
# -------------------------

MIN_GROUP_SIZE = 3
LOW_PRICE_RATIO_THRESHOLD = 0.80
CROSS_PLATFORM_GAP_RATIO_THRESHOLD = 0.25


# -------------------------
# 2. 显式业务低价规则
# -------------------------

EXPLICIT_LOW_PRICE_RULES = [
    {"brand": "鸿茅", "spec": "500ml", "threshold": 180.0},
    {"brand": "鸿茅", "spec": "500ml*4瓶", "threshold": 799.0}
]


# -------------------------
# 3. 列名映射
# -------------------------

COLUMN_CANDIDATES = {
    "raw_title": ["对照标题", "raw_title", "商品标题"],
    "raw_price": ["对照价格", "raw_price", "商品价格"],
    "raw_platform": ["对照平台", "raw_platform", "平台"],
    "raw_date": ["对照日期", "raw_date", "日期"],
    "raw_spec": ["对照规格", "raw_spec", "规格"],

    "clean_title": ["干净标题", "clean_title"],
    "clean_spec": ["干净规格", "clean_spec"],
    "price": ["干净价格", "price"],
    "normalized_platform": ["干净平台", "normalized_platform"],
    "date": ["干净日期", "date"],

    "missing_price_flag": ["价格质量标记", "missing_price_flag"],
    "missing_date_flag": ["日期质量标记", "missing_date_flag"],
    "unknown_platform_flag": ["未知平台标志", "unknown_platform_flag"],
    "missing_spec_flag": ["规格质量标记", "missing_spec_flag"],

    "normalized_brand": ["标准化品牌", "normalized_brand"],
    "title_spec_hint": ["标题规范提示", "title_spec_hint"],
    "normalized_spec": ["规范化规格", "normalized_spec"],
    "spec_source": ["规范来源", "spec_source"],
    "title_spec_mismatch_flag": ["标题规格不匹配标志", "title_spec_mismatch_flag"],
    "missing_brand_flag": ["缺失品牌标志", "missing_brand_flag"],
    "missing_normalized_spec_flag": ["缺少规范化规范标志", "missing_normalized_spec_flag"],
}


INTERNAL_ANALYSIS_COLS = [
    "group_sample_count",
    "group_avg_price",
    "group_min_price",
    "group_max_price",
    "price_vs_group_mean_ratio",
    "cross_platform_gap_ratio",
    "explicit_low_price_threshold",
    "is_explicit_low_price",
    "is_stat_low_price",
    "low_price_rule_source",
    "is_low_price_anomaly",
    "is_cross_platform_anomaly",
    "is_spec_risk",
    "is_any_anomaly",
    "anomaly_reason",
]


# -------------------------
# 4. 基础读写
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


def save_csv(df: pd.DataFrame, output_path: Union[str, Path]) -> None:
    """
    保存 CSV 文件。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


# -------------------------
# 5. 小工具
# -------------------------

def find_first_existing_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    normalized_map = {
        str(col).replace("\ufeff", "").strip(): col
        for col in df.columns
    }

    for candidate in candidates:
        key = str(candidate).replace("\ufeff", "").strip()
        if key in normalized_map:
            return normalized_map[key]

    return None


def standardize_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    不直接改原始中文列，而是额外补一套内部标准列，方便后面统一分析。
    """
    result = df.copy()
    result.columns = [str(col).replace("\ufeff", "").strip() for col in result.columns]

    for canonical_col, candidates in COLUMN_CANDIDATES.items():
        actual_col = find_first_existing_column(result, candidates)
        if actual_col is not None:
            result[canonical_col] = result[actual_col]

    return result


def safe_to_bool(value: object) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes"}


def get_explicit_low_price_threshold(brand: object, spec: object) -> Optional[float]:
    brand_text = "" if pd.isna(brand) else str(brand).strip()
    spec_text = "" if pd.isna(spec) else str(spec).strip()

    for rule in EXPLICIT_LOW_PRICE_RULES:
        if brand_text == rule["brand"] and spec_text == rule["spec"]:
            return float(rule["threshold"])

    return None


def get_low_price_rule_source(row: pd.Series) -> str:
    explicit_hit = bool(row.get("is_explicit_low_price", False))
    stat_hit = bool(row.get("is_stat_low_price", False))

    if explicit_hit and stat_hit:
        return "both"
    if explicit_hit:
        return "explicit_rule"
    if stat_hit:
        return "stat_rule"
    return ""


def build_anomaly_reason(row: pd.Series) -> str:
    reasons = []

    if safe_to_bool(row.get("is_low_price_anomaly", False)):
        rule_source = str(row.get("low_price_rule_source", "")).strip()
        explicit_threshold = row.get("explicit_low_price_threshold")
        avg_price = row.get("group_avg_price")
        ratio = row.get("price_vs_group_mean_ratio")
        current_price = row.get("price")

        if rule_source == "explicit_rule" and pd.notna(explicit_threshold) and pd.notna(current_price):
            reasons.append(
                f"疑似异常低价：命中显式阈值规则，阈值<{explicit_threshold:.2f}，当前价格={current_price:.2f}"
            )
        elif (
            rule_source == "both"
            and pd.notna(explicit_threshold)
            and pd.notna(avg_price)
            and pd.notna(ratio)
        ):
            reasons.append(
                f"疑似异常低价：同时命中显式阈值与统计规则，阈值<{explicit_threshold:.2f}，均价={avg_price:.2f}，当前/均价={ratio:.2f}"
            )
        elif pd.notna(avg_price) and pd.notna(ratio):
            reasons.append(
                f"疑似异常低价：当前价格低于同品牌同规格均价，均价={avg_price:.2f}，当前/均价={ratio:.2f}"
            )
        else:
            reasons.append("疑似异常低价")

    if safe_to_bool(row.get("is_cross_platform_anomaly", False)):
        min_price = row.get("group_min_price")
        max_price = row.get("group_max_price")
        gap_ratio = row.get("cross_platform_gap_ratio")
        if pd.notna(min_price) and pd.notna(max_price) and pd.notna(gap_ratio):
            reasons.append(
                f"跨平台价差过大：最低价={min_price:.2f}，最高价={max_price:.2f}，价差比例={gap_ratio:.2f}"
            )
        else:
            reasons.append("跨平台价差过大")

    if safe_to_bool(row.get("is_spec_risk", False)):
        clean_spec = row.get("clean_spec", "")
        title_spec_hint = row.get("title_spec_hint", "")
        if str(clean_spec).strip() and str(title_spec_hint).strip():
            reasons.append(f"规格识别风险：规格列={clean_spec}，标题规格={title_spec_hint}")
        elif safe_to_bool(row.get("missing_normalized_spec_flag", False)):
            reasons.append("规格识别风险：归一规格缺失")
        else:
            reasons.append("规格识别风险")

    return "；".join(reasons)


# -------------------------
# 6. 规则计算
# -------------------------

def attach_group_stats(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    group_cols = ["normalized_brand", "normalized_spec"]

    stats = (
        result.groupby(group_cols, dropna=False)
        .agg(
            group_sample_count=("price", lambda s: s.notna().sum()),
            group_avg_price=("price", "mean"),
            group_min_price=("price", "min"),
            group_max_price=("price", "max"),
        )
        .reset_index()
    )

    result = result.merge(stats, on=group_cols, how="left")

    result["price_vs_group_mean_ratio"] = result.apply(
        lambda row: (
            row["price"] / row["group_avg_price"]
            if pd.notna(row["price"]) and pd.notna(row["group_avg_price"]) and row["group_avg_price"] != 0
            else pd.NA
        ),
        axis=1,
    )

    result["cross_platform_gap_ratio"] = result.apply(
        lambda row: (
            (row["group_max_price"] - row["group_min_price"]) / row["group_max_price"]
            if pd.notna(row["group_max_price"]) and pd.notna(row["group_min_price"]) and row["group_max_price"] != 0
            else pd.NA
        ),
        axis=1,
    )

    return result


def detect_low_price_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    result["explicit_low_price_threshold"] = result.apply(
        lambda row: get_explicit_low_price_threshold(
            row.get("normalized_brand"),
            row.get("normalized_spec"),
        ),
        axis=1,
    )

    result["is_explicit_low_price"] = result.apply(
        lambda row: (
            pd.notna(row["price"])
            and pd.notna(row["explicit_low_price_threshold"])
            and row["price"] < row["explicit_low_price_threshold"]
        ),
        axis=1,
    )

    result["is_stat_low_price"] = result.apply(
        lambda row: (
            pd.notna(row["price"])
            and pd.notna(row["group_avg_price"])
            and row["group_sample_count"] >= MIN_GROUP_SIZE
            and row["price"] < row["group_avg_price"] * LOW_PRICE_RATIO_THRESHOLD
        ),
        axis=1,
    )

    result["low_price_rule_source"] = result.apply(get_low_price_rule_source, axis=1)

    result["is_low_price_anomaly"] = result.apply(
        lambda row: bool(row["is_explicit_low_price"]) or bool(row["is_stat_low_price"]),
        axis=1,
    )

    return result


def detect_cross_platform_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    result["is_cross_platform_anomaly"] = result.apply(
        lambda row: (
            pd.notna(row["price"])
            and pd.notna(row["group_min_price"])
            and pd.notna(row["cross_platform_gap_ratio"])
            and row["group_sample_count"] >= MIN_GROUP_SIZE
            and row["cross_platform_gap_ratio"] >= CROSS_PLATFORM_GAP_RATIO_THRESHOLD
            and row["price"] == row["group_min_price"]
        ),
        axis=1,
    )

    return result


def detect_spec_risk(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    result["is_spec_risk"] = result.apply(
        lambda row: (
            safe_to_bool(row.get("title_spec_mismatch_flag", False))
            or safe_to_bool(row.get("missing_normalized_spec_flag", False))
        ),
        axis=1,
    )

    return result


# -------------------------
# 7. 输出整理
# -------------------------

def finalize_output_df(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    # 如果原表没有这些中文列，就从内部标准列回填一份
    fallback_pairs = {
        "对照标题": "raw_title",
        "对照价格": "raw_price",
        "对照平台": "raw_platform",
        "对照日期": "raw_date",
        "对照规格": "raw_spec",
        "干净标题": "clean_title",
        "干净规格": "clean_spec",
        "干净价格": "price",
        "干净平台": "normalized_platform",
        "干净日期": "date",
        "标准化品牌": "normalized_brand",
        "标题规范提示": "title_spec_hint",
        "规范化规格": "normalized_spec",
        "规范来源": "spec_source",
        "标题规格不匹配标志": "title_spec_mismatch_flag",
        "缺失品牌标志": "missing_brand_flag",
        "缺少规范化规范标志": "missing_normalized_spec_flag",
        "价格质量标记": "missing_price_flag",
        "日期质量标记": "missing_date_flag",
        "未知平台标志": "unknown_platform_flag",
        "规格质量标记": "missing_spec_flag",
    }

    for zh_col, inner_col in fallback_pairs.items():
        if zh_col not in result.columns and inner_col in result.columns:
            result[zh_col] = result[inner_col]

    # 新增分析列统一转中文
    result["组内有效价格样本数"] = result["group_sample_count"]
    result["组内均价"] = result["group_avg_price"]
    result["组内最低价"] = result["group_min_price"]
    result["组内最高价"] = result["group_max_price"]
    result["当前价格/组均价比"] = result["price_vs_group_mean_ratio"]
    result["跨平台价差比例"] = result["cross_platform_gap_ratio"]
    result["显式低价阈值"] = result["explicit_low_price_threshold"]
    result["命中显式低价规则"] = result["is_explicit_low_price"]
    result["命中统计低价规则"] = result["is_stat_low_price"]
    result["低价规则来源"] = result["low_price_rule_source"]
    result["是否疑似异常低价"] = result["is_low_price_anomaly"]
    result["是否跨平台价差异常"] = result["is_cross_platform_anomaly"]
    result["是否规格识别风险"] = result["is_spec_risk"]
    result["是否存在任一异常"] = result["is_any_anomaly"]
    result["异常原因"] = result["anomaly_reason"]

    preferred_cols = [
        "商品标题",
        "规格",
        "商品价格",
        "平台",
        "日期",
        "对照标题",
        "对照价格",
        "对照平台",
        "对照日期",
        "对照规格",
        "干净标题",
        "干净规格",
        "干净价格",
        "干净平台",
        "干净日期",
        "价格质量标记",
        "日期质量标记",
        "未知平台标志",
        "规格质量标记",
        "标准化品牌",
        "标题规范提示",
        "规范化规格",
        "规范来源",
        "标题规格不匹配标志",
        "缺失品牌标志",
        "缺少规范化规范标志",
        "组内有效价格样本数",
        "组内均价",
        "组内最低价",
        "组内最高价",
        "当前价格/组均价比",
        "跨平台价差比例",
        "显式低价阈值",
        "命中显式低价规则",
        "命中统计低价规则",
        "低价规则来源",
        "是否疑似异常低价",
        "是否跨平台价差异常",
        "是否规格识别风险",
        "是否存在任一异常",
        "异常原因",
    ]

    existing_cols = [col for col in preferred_cols if col in result.columns]

    internal_cols = list(COLUMN_CANDIDATES.keys()) + INTERNAL_ANALYSIS_COLS
    other_cols = [col for col in result.columns if col not in existing_cols and col not in internal_cols]

    result = result[existing_cols + other_cols]
    return result


# -------------------------
# 8. 主分析流程
# -------------------------

def run_analysis(df: pd.DataFrame) -> pd.DataFrame:
    result = standardize_analysis_columns(df)

    required_cols = [
        "normalized_brand",
        "normalized_spec",
        "price",
        "normalized_platform",
        "clean_spec",
        "title_spec_hint",
        "title_spec_mismatch_flag",
        "missing_normalized_spec_flag",
    ]
    missing_cols = [col for col in required_cols if col not in result.columns]
    if missing_cols:
        raise ValueError(
            f"缺少必要列：{missing_cols}，请先运行 normalizer.py 生成标准化结果文件。"
        )

    result["price"] = pd.to_numeric(result["price"], errors="coerce")

    result = attach_group_stats(result)
    result = detect_low_price_anomaly(result)
    result = detect_cross_platform_anomaly(result)
    result = detect_spec_risk(result)

    result["is_any_anomaly"] = result.apply(
        lambda row: (
            safe_to_bool(row["is_low_price_anomaly"])
            or safe_to_bool(row["is_cross_platform_anomaly"])
            or safe_to_bool(row["is_spec_risk"])
        ),
        axis=1,
    )

    result["anomaly_reason"] = result.apply(build_anomaly_reason, axis=1)

    result = finalize_output_df(result)
    return result


# -------------------------
# 9. 验收辅助函数（按中文列）
# -------------------------

def get_suspected_low_price_items(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[df["是否疑似异常低价"] == True][
            [
                "标准化品牌",
                "规范化规格",
                "干净平台",
                "干净价格",
                "显式低价阈值",
                "组内均价",
                "当前价格/组均价比",
                "低价规则来源",
                "异常原因",
            ]
        ]
        .sort_values(["标准化品牌", "规范化规格", "干净价格"], ascending=[True, True, True])
        .reset_index(drop=True)
    )


def get_spec_risk_items(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[df["是否规格识别风险"] == True][
            [
                "标准化品牌",
                "干净标题",
                "干净规格",
                "标题规范提示",
                "规范化规格",
                "异常原因",
            ]
        ]
        .sort_values(["标准化品牌", "干净标题"])
        .reset_index(drop=True)
    )


def count_low_price_by_platform(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[df["是否疑似异常低价"] == True]
        .groupby("干净平台", dropna=False)
        .size()
        .reset_index(name="低价数量")
        .sort_values("低价数量", ascending=False)
        .reset_index(drop=True)
    )


def max_price_gap_by_brand(df: pd.DataFrame) -> pd.DataFrame:
    group_gap_df = (
        df.groupby(["标准化品牌", "规范化规格"], dropna=False)
        .agg(
            最高价=("干净价格", "max"),
            最低价=("干净价格", "min"),
        )
        .reset_index()
    )

    group_gap_df["价差金额"] = group_gap_df["最高价"] - group_gap_df["最低价"]
    group_gap_df["价差比例"] = group_gap_df.apply(
        lambda row: (
            row["价差金额"] / row["最高价"]
            if pd.notna(row["最高价"]) and row["最高价"] != 0
            else pd.NA
        ),
        axis=1,
    )

    brand_gap_df = (
        group_gap_df.sort_values(["标准化品牌", "价差金额"], ascending=[True, False])
        .groupby("标准化品牌", as_index=False)
        .first()
        .sort_values("价差金额", ascending=False)
        .reset_index(drop=True)
    )

    return brand_gap_df


# -------------------------
# 10. 本地调试入口
# -------------------------

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    input_path = project_root / "data" / "normalized_products_preview.csv"
    output_path = project_root / "data" / "异常明细.csv"

    print("实际读取文件：", input_path)

    raw_df = load_csv(input_path)
    analyzed_df = run_analysis(raw_df)
    save_csv(analyzed_df, output_path)

    print("异常规则分析完成。")
    print(f"输入文件: {input_path}")
    print(f"输出文件: {output_path}")

    print("\n疑似异常低价数量：", int(analyzed_df["是否疑似异常低价"].sum()))
    print("跨平台价差异常数量：", int(analyzed_df["是否跨平台价差异常"].sum()))
    print("规格识别风险数量：", int(analyzed_df["是否规格识别风险"].sum()))

    print("\n哪个平台低价最多：")
    print(count_low_price_by_platform(analyzed_df))

    print("\n哪个品牌跨平台价差最大：")
    print(max_price_gap_by_brand(analyzed_df).head())

    print("\n前 5 条异常明细预览：")
    print(analyzed_df[analyzed_df["是否存在任一异常"] == True].head())
