# -*- coding: utf-8 -*-
"""
创建时间    :2026/03/28 20:29
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import re
from pathlib import Path
from typing import Optional, Union
import pandas as pd

# 基础字段识别

TITLE_CANDIDATES = ["title", "product_title", "raw_title", "商品标题", "标题"]
PRICE_CANDIDATES = ["price", "商品价格", "售价", "到手价", "final_price"]
PLATFORM_CANDIDATES = ["platform", "平台", "site", "channel"]
DATE_CANDIDATES = ["date", "日期", "scraped_at", "crawl_time", "时间", "created_at"]
SPEC_CANDIDATES = ["spec", "规格", "商品规格", "规格参数", "package_spec", "容量规格"]


def find_first_existing_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """
    在 DataFrame 中按候选列名顺序寻找第一个存在的列。
    会自动清理 BOM、首尾空格。
    """
    normalized_map = {
        str(col).replace("\ufeff", "").strip(): col
        for col in df.columns
    }

    for candidate in candidates:
        key = str(candidate).replace("\ufeff", "").strip()
        if key in normalized_map:
            return normalized_map[key]

    return None


# 单字段清洗函数
def clean_title_text(title: object) -> str:
    """
    商品标题基础清洗：
    -去掉多余空白
    -去掉常见营销噪声
    -保留核心商品信息
    """
    if pd.isna(title):
        return ""
    text = str(title).strip()

    # 统一中括号
    text = text.replace("【", "[").replace("】", "]")

    # 去掉多余空白
    text = re.sub(r"\s+", " ", text)

    # 常见营销噪音词
    noise_patterns = [
        r"正品保障",
        r"官方旗舰店",
        r"旗舰店",
        r"限时秒杀",
        r"买1送1",
        r"买一送一",
        r"包邮",
        r"领券立减",
        r"假一赔十",
        r"新品上市",
        r"热卖爆款",
        r"七天无理由退换",
    ]

    for pattern in noise_patterns:
        text = re.sub(pattern, "", text)

    text = re.sub(r"\s+", " ", text).strip()
    return text


# 规格基础清洗
def clean_spec_text(spec: object) -> str:
    """
    规格基础清洗
    - 去掉多余空白
    - 统一部分常见单位写法
    - 这里采用清清洗
    """
    if pd.isna(spec):
        return ""

    text = str(spec).strip()
    text = re.sub(r"\s+", "", text)

    # 统一常见单位
    text = text.replace("ML", "ml").replace("Ml", "ml")
    text = text.replace("毫升", "ml")
    text = text.replace("L", "l")
    return text


# 从文本中提取价格
def extract_price_from_text(text: str) -> Optional[float]:
    """
    从文本中提取价格,支持：
    - 到手价29.9元
    - 券后39元
    - ¥29.90
    - 29.9元
    """
    if not text:
        return None

    patterns = [
        r"(?:到手价|券后价|券后|活动价|售价|现价)\s*[:：]?\s*[¥￥]?\s*(\d+(?:\.\d+)?)\s*元?",
        r"[¥￥]\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*元",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                price = float(match.group(1))
                if price > 0:
                    return price
            except ValueError:
                return None

    return None


# 价格清洗
def clean_price_value(value: object, fallback_title: str = "") -> Optional[float]:
    """
    价格清洗:
    - 优先清洗价格列
    - 如果价格列缺失，再尝试从标题中提取
    """

    if not pd.isna(value):
        text = str(value).strip()
        text = text.replace(",", "")
        text = text.replace("￥", "").replace("¥", "")
        text = text.replace("元", "").strip()

        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            try:
                price = float(match.group(1))
                if price > 0:
                    return price
            except ValueError:
                pass

    return extract_price_from_text(fallback_title)


# 平台清洗与基础归并。
def clean_platform_value(value: object) -> str:
    """
    平台清洗与基础归并，第二周这里只进行轻量统一。
    """
    if pd.isna(value):
        return "未知平台"

    text = str(value).strip().lower()

    mapping = {
        "jd": "京东",
        "京东": "京东",
        "京东自营": "京东",
        "jingdong": "京东",

        "tb": "淘宝",
        "taobao": "淘宝",
        "淘宝": "淘宝",
        "天猫": "淘宝",

        "pdd": "拼多多",
        "拼多多": "拼多多",
        "拼夕夕": "拼多多",
        "pinduoduo": "拼多多",

        "抖音": "抖音",
        "douyin": "抖音",

        "美团": "美团",
        "meituan": "美团",

        "饿了么": "饿了么",
        "eleme": "饿了么",
        "淘宝闪购": "饿了么",
    }
    return mapping.get(text, str(value).strip())


# 时间清洗
def clean_datetime_value(value: object) -> pd.Timestamp:
    """
    时间清洗：
    支持这些常见格式：
    - 2026-03-18
    - 2026/03/19
    - 2026年03月20日
    - 03-21
    - 3月21日
    - 2026-03-22 10:30:00
    - 2026/03/23 09:15

    对于不带年份的日期，默认补 2026 年。
    无法识别时返回 NaT。
    """
    if pd.isna(value):
        return pd.NaT

    text = str(value).strip()
    if not text:
        return pd.NaT

    # 先做基础清理
    text = text.replace("：", ":").strip()

    # 1) 先直接让 pandas 试一次
    dt = pd.to_datetime(text, errors="coerce")
    if pd.notna(dt):
        return dt

    # 2) 处理中文年月日：2026年03月20日 / 2026年3月20日
    match = re.match(r"^\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*$", text)
    if match:
        year, month, day = map(int, match.groups())
        try:
            return pd.Timestamp(year=year, month=month, day=day)
        except ValueError:
            return pd.NaT

    # 3) 处理中文月日：3月21日 / 03月21日，默认补 2026 年
    match = re.match(r"^\s*(\d{1,2})月(\d{1,2})日\s*$", text)
    if match:
        month, day = map(int, match.groups())
        try:
            return pd.Timestamp(year=2026, month=month, day=day)
        except ValueError:
            return pd.NaT

    # 4) 处理短横线月日：03-21 / 3-21，默认补 2026 年
    match = re.match(r"^\s*(\d{1,2})-(\d{1,2})\s*$", text)
    if match:
        month, day = map(int, match.groups())
        try:
            return pd.Timestamp(year=2026, month=month, day=day)
        except ValueError:
            return pd.NaT

    return pd.NaT


# DataFrame 级别处理
def normalize_input_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    把输入 DataFrame 整理成统一字段结构，
    为后续清洗和分析打基础。
    """
    result = df.copy()

    # 先统一清理列名
    result.columns = [str(col).replace("\ufeff", "").strip() for col in result.columns]

    print("normalize_input_dataframe 读取到的列名：", result.columns.tolist())

    title_col = find_first_existing_column(result, TITLE_CANDIDATES)
    price_col = find_first_existing_column(result, PRICE_CANDIDATES)
    platform_col = find_first_existing_column(result, PLATFORM_CANDIDATES)
    date_col = find_first_existing_column(result, DATE_CANDIDATES)
    spec_col = find_first_existing_column(result, SPEC_CANDIDATES)

    if title_col is None:
        raise ValueError(
            f"CSV 中未找到标题列。当前实际列名为：{result.columns.tolist()}，"
            "请至少包含 title / 商品标题 / 标题 之一。"
        )

    result["raw_title"] = result[title_col]
    result["raw_price"] = result[price_col] if price_col else None
    result["raw_platform"] = result[platform_col] if platform_col else None
    result["raw_date"] = result[date_col] if date_col else None
    result["raw_spec"] = result[spec_col] if spec_col else None

    return result


def run_basic_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    """
        第二周第一阶段：
        - 标准化输入列
        - 基础清洗标题、规格、价格、平台、时间
    """
    result = normalize_input_dataframe(df)

    result['clean_title'] = result['raw_title'].apply(clean_title_text)
    result['clean_spec'] = result['raw_spec'].apply(clean_spec_text)
    result['price'] = result.apply(lambda row: clean_price_value(row['raw_price'], row['raw_title']), axis=1)
    result['normalized_platform'] = result["raw_platform"].apply(clean_platform_value)
    result['date'] = result['raw_date'].apply(clean_datetime_value)

    # 基础质量标记
    result['missing_price_flag'] = result['price'].isna()
    result['missing_date_flag'] = result['date'].isna()
    result['unknown_platform_flag'] = result['normalized_platform'].eq("未知平台")
    result['missing_spec_flag'] = result['clean_spec'].eq("")

    preferred_cols = [
        "raw_title",
        "clean_title",
        "raw_spec",
        "clean_spec",
        "raw_price",
        "price",
        "raw_platform",
        "normalized_platform",
        "raw_date",
        "date",
        "missing_price_flag",
        "missing_date_flag",
        "unknown_platform_flag",
        "missing_spec_flag",
    ]
    existing_cols = [col for col in preferred_cols if col in result.columns]
    other_cols = [col for col in result.columns if col not in existing_cols]

    result = result[existing_cols + other_cols]
    return result


# 文件写入
def load_csv(csv_path: Union[str, Path]) -> pd.DataFrame:
    """
    读取 CSV 文件：
    - 优先处理 utf-8-sig / utf-8 / gbk / gb18030
    - 强制按逗号分隔
    - 如果默认 C 引擎失败，则回退到 python 引擎
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"未找到文件：{csv_path}")

    encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030"]
    last_error = None

    for enc in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=enc, sep=",")
            df.columns = [str(col).replace("\ufeff", "").strip() for col in df.columns]
            return df
        except (UnicodeDecodeError, pd.errors.ParserError) as e:
            last_error = e
            try:
                df = pd.read_csv(csv_path, encoding=enc, sep=",", engine="python")
                df.columns = [str(col).replace("\ufeff", "").strip() for col in df.columns]
                return df
            except (UnicodeDecodeError, pd.errors.ParserError) as e2:
                last_error = e2
                continue

    raise ValueError(f"CSV 读取失败，请检查文件编码或格式：{csv_path}\n最后错误：{last_error}")


# 保存清洗后的csv
def save_cleaned_csv(df: pd.DataFrame, output_path: Union[str, Path]) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


# 本地调试入口
if __name__ == '__main__':
    project_root = Path(__file__).resolve().parents[2]
    input_path = project_root / "data" / "sample_products.csv"
    output_path = project_root / "data" / "cleaned_products_preview.csv"
    print("实际读取文件：", input_path)

    raw_df = load_csv(input_path)
    cleaned_df = run_basic_cleaning(raw_df)
    save_cleaned_csv(cleaned_df, output_path)

    print("基础清洗完成。")
    print(f"输入文件: {input_path}")
    print(f"输出文件: {output_path}")
    print("\n清洗后前 5 行预览：")
    print(cleaned_df.head())
