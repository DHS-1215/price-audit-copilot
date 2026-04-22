# -*- coding: utf-8 -*-
"""
创建时间    :2026/03/29 12:08
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import re
from pathlib import Path
from typing import Optional, Union
import pandas as pd

# 品牌别名字典
BRAND_ALIAS_MAP = {
    "同仁堂": ["北京同仁堂", "同仁堂"],
    "鸿茅": ["鸿茅药酒", "鸿茅"],
    "东阿阿胶": ["东阿阿胶"],
    "广誉远": ["广誉远"],
    "九芝堂": ["九芝堂"],
    "天益寿气血固本": ["天益寿"],
}


# 基础工具函数
def load_csv(csv_path: Union[str, Path]) -> pd.DataFrame:
    """
    :param csv_path: 读取csv文件地址
    优先编码utf-8-sig，不行再尝试 utf-8 / gbk / gb18030
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

    raise ValueError(f"csv 读取失败：{csv_path}\n最后错误：{last_error}")


# 保存csv
def save_csv(df: pd.DataFrame, output_path: Union[str, Path]) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')


# 规格数字格式化
def format_number(value: float) -> str:
    """
    规格数字格式化：
    20.0 -> 20
    20.5 -> 20.5
    """
    if float(value).is_integer():
        return str(int(value))
    return str(value).rstrip('0').rstrip('.')


# 简单中文数字转阿拉伯数字。
def chinese_num_to_int(text: str) -> Optional[int]:
    """
    简单中文数字转阿拉伯数字。
    支持：
    一 二 三 四 五 六 七 八 九 十 十一 十二 二十 二十一 两
    """
    if not text:
        return None

    if text.isdigit():
        return int(text)

    mapping = {
        "零": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }

    if text == "十":
        return 10

    if "十" in text:
        parts = text.strip("十")
        left = parts[0]
        right = parts[1] if len(parts) > 1 else ""

        tens = 1 if left == "" else mapping.get(left)
        ones = 0 if right == "" else mapping.get(right)

        if tens is None or ones is None:
            return None
        return tens * 10 + ones

    return mapping.get(text)


# 通用文本基础清理
def normalize_basic_text(text: object) -> str:
    if text is None or pd.isna(text):
        return ""

    s = str(text).strip()
    s = s.replace("\ufeff", "")
    s = s.replace("【", "[").replace("】", "]")
    s = s.replace("：", ":")
    s = re.sub(r"\s+", "", s)

    # 统一乘号
    s = s.replace("×", "*").replace("X", "*").replace("x", "*")

    # 统一单位
    s = s.replace("ML", "ml").replace("Ml", "ml")
    s = s.replace("毫升", "ml")
    s = s.replace("克", "g")
    s = s.replace("KG", "kg").replace("Kg", "kg")
    s = s.replace("公斤", "kg")

    return s


# 品牌归一,从标题中抽取并归一品牌。
def extract_brand_from_title(title: object) -> str:
    text = normalize_basic_text(title)
    if not text:
        return ""

    # 先按别名长度从长到短匹配，避免“鸿茅药酒”先被“鸿茅”截走也无所谓，
    # 但长词优先更稳。
    aias_pairs = []
    for std_brand, aliases in BRAND_ALIAS_MAP.items():
        for alias in aliases:
            aias_pairs.append((alias, std_brand))

    aias_pairs.sort(key=lambda x: len(x[0]), reverse=True)

    for alias, std_brand in aias_pairs:
        if alias in text:
            return std_brand

    return ""


# 规格抽取
def replace_chinese_count_patterns(text: str) -> str:
    """
    把：
    九袋装 -> 9袋装
    六丸装 -> 6丸装
    十二支装 -> 12支装
    三十袋/盒 -> 30袋/盒
    """
    if not text:
        return text

    def repl(match: re.Match) -> str:
        num_text = match.group(1)
        unit_1 = match.group(2)
        unit_2 = match.group(3) if match.lastindex and match.lastindex >= 3 else ""

        value = chinese_num_to_int(num_text)
        if value is None:
            return match.group(0)

        if unit_2:
            return f"{value}{unit_1}/{unit_2}"
        return f"{value}{unit_1}装"

    # 中文数字 + 单位 + 装
    text = re.sub(
        r"([零一二两三四五六七八九十]+)(袋|支|丸|片|粒|盒|瓶)装",
        repl,
        text
    )

    # 中文数字 + 单位/单位
    text = re.sub(
        r"([零一二两三四五六七八九十]+)(袋|支|丸|片|粒)/(盒|瓶|袋)",
        repl,
        text
    )

    return text


# 规格归一,目标是把明显等价的写法统一.
def normalize_spec_value(spec: object) -> str:
    """
    规格归一：
    目标是把明显等价的写法统一，不追求工业级。
    """
    text = normalize_basic_text(spec)
    if not text:
        return ""

    text = replace_chinese_count_patterns(text)

    # 1) 20ml*12支 / 20ML*12支
    match = re.match(r"^(\d+(?:\.\d+)?)(ml|g|kg|l)\*(\d+)(支|袋|盒|瓶|丸|片|粒)$", text)
    if match:
        num, unit, count, pack_unit = match.groups()
        return f"{format_number(float(num))}{unit}*{int(count)}{pack_unit}"

    # 2) 9袋/盒 / 30袋/盒 / 6丸/盒
    match = re.match(r"^(\d+)(袋|支|丸|片|粒)/(盒|瓶|袋)$", text)
    if match:
        count, item_unit, pack_unit = match.groups()
        return f"{int(count)}{item_unit}/{pack_unit}"

    # 3) 12支装 / 9袋装 / 6丸装
    match = re.match(r"^(\d+)(袋|支|丸|片|粒|盒|瓶)装$", text)
    if match:
        count, unit = match.groups()
        return f"{int(count)}{unit}装"

    # 4) 500ml / 250g / 1l
    match = re.match(r"^(\d+(?:\.\d+)?)(ml|g|kg|l)$", text)
    if match:
        num, unit = match.groups()
        return f"{format_number(float(num))}{unit}"

    # 5) 500ml/瓶
    match = re.match(r"^(\d+(?:\.\d+)?)(ml|g|kg|l)/(瓶|盒|袋)$", text)
    if match:
        num, unit, pack_unit = match.groups()
        return f"{format_number(float(num))}{unit}/{pack_unit}"

    return text


# 从标题中提取一个规格提示值
def extract_spec_from_title(title: object) -> str:
    """
    从标题中提取规格提示值 title_spec_hint。
    优先识别更强的规格信息，避免先抓到 1盒装 这种弱包装信息。
    """
    text = normalize_basic_text(title)
    if not text:
        return ""

    text = replace_chinese_count_patterns(text)

    patterns = [
        # 20ml*12支
        r"(\d+(?:\.\d+)?(?:ml|g|kg|l)\*\d+(?:支|袋|盒|瓶|丸|片|粒))",
        # 9袋/盒、30袋/盒、6丸/盒
        r"(\d+(?:袋|支|丸|片|粒)/(?:盒|瓶|袋))",
        # 500ml/瓶
        r"(\d+(?:\.\d+)?(?:ml|g|kg|l)/(?:瓶|盒|袋))",
        # 500ml、250g、1l
        r"(\d+(?:\.\d+)?(?:ml|g|kg|l))",
        # 12支装、9袋装、6丸装
        r"(\d+(?:袋|支|丸|片|粒)装)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_spec_value(match.group(1))

    return ""


# 选择最终规格
def choose_final_spec(clean_spec: object, title_spec_hint: object) -> tuple[str, str]:
    """
    选择最终规格：
    - 优先使用清洗后的规格列
    - 如果规格列为空，则回退到标题提取
    返回：
    (normalized_spec, spec_source)
    """
    spec_from_col = normalize_spec_value(clean_spec)
    spec_from_title = normalize_spec_value(title_spec_hint)

    if spec_from_col:
        return spec_from_col, "spec_column"

    if spec_from_title:
        return spec_from_title, "title_fallback"

    return "", "missing"


# 把规格转成比较口径，尽量减少“表达不同但本质一致”的误报。
def canonicalize_spec_for_compare(spec: object) -> str:
    """
    把规格转成比较口径，尽量减少“表达不同但本质一致”的误报。
    例如：
    - 9袋装 -> 9袋
    - 9袋/盒 -> 9袋
    - 6丸装 -> 6丸
    - 6丸/盒 -> 6丸
    - 20ml*12支 -> 12支
    - 500ml -> 500ml
    - 250ml -> 250ml
    """
    s = normalize_spec_value(spec)
    if not s:
        return ""

    # 9袋装 -> 9袋
    match = re.match(r"^(\d+)(袋|支|丸|片|粒)装$", s)
    if match:
        count, unit = match.groups()
        return f"{int(count)}{unit}"

    # 9袋/盒 -> 9袋
    match = re.match(r"^(\d+)(袋|支|丸|片|粒)/(盒|瓶|袋)$", s)
    if match:
        count, unit, _ = match.groups()
        return f"{int(count)}{unit}"

    # 20ml*12支 -> 12支
    match = re.match(r"^(\d+(?:\.\d+)?)(ml|g|kg|l)\*(\d+)(支|袋|盒|瓶|丸|片|粒)$", s)
    if match:
        _, _, count, unit = match.groups()
        return f"{int(count)}{unit}"

    return s


# 判断标题规格和规格列是否真的不一致。
def is_title_spec_mismatch(clean_spec: object, title_spec_hint: object) -> bool:
    left = canonicalize_spec_for_compare(clean_spec)
    right = canonicalize_spec_for_compare(title_spec_hint)
    if not left or not right:
        return False

    return left != right


# DataFrame 级别归一
def run_normalization(df: pd.DataFrame) -> pd.DataFrame:
    """
    第二周第二阶段：
    - 品牌归一
    - 规格归一
    - 产出标题规格提示和一致性辅助列
    """
    result = df.copy()
    result.columns = [str(col).replace("\ufeff", "").strip() for col in result.columns]

    required_cols = ["干净标题", "干净规格"]
    missing_cols = [col for col in required_cols if col not in result.columns]
    if missing_cols:
        raise ValueError(f"缺少必要列：{missing_cols}，请先运行 cleaner.py 生成 cleaned_products_preview.csv")

    # 品牌归一
    result["标准化品牌"] = result["干净标题"].apply(extract_brand_from_title)

    # 从标题提规格提示
    result["标题规范提示"] = result["干净标题"].apply(extract_spec_from_title)

    # 最终规格 + 来源
    spec_results = result.apply(
        lambda row: choose_final_spec(row["干净规格"], row["标题规范提示"]),
        axis=1
    )

    result["规范化规格"] = spec_results.apply(lambda x: x[0])
    result["规范来源"] = spec_results.apply(lambda x: x[1])

    # 标题规格与规格列是否不一致
    result["标题规格不匹配标志"] = result.apply(
        lambda row: is_title_spec_mismatch(row["干净规格"], row["标题规范提示"]),
        axis=1
    )

    result["缺失品牌标志"] = result["标准化品牌"].eq("")
    result["缺少规范化规范标志"] = result["规范化规格"].eq("")

    preferred_cols = [
        "raw_title",
        "clean_title",
        "normalized_brand",
        "raw_spec",
        "clean_spec",
        "title_spec_hint",
        "normalized_spec",
        "spec_source",
        "title_spec_mismatch_flag",
        "missing_brand_flag",
        "missing_normalized_spec_flag",
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


# 本地调试入口
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    input_path = project_root / "data" / "cleaned_products_preview.csv"
    output_path = project_root / "data" / "normalized_products_preview.csv"

    print("实际读取文件：", input_path)

    raw_df = load_csv(input_path)
    normalized_df = run_normalization(raw_df)
    save_csv(normalized_df, output_path)

    print("品牌归一 + 规格归一完成。")
    print(f"输入文件: {input_path}")
    print(f"输出文件: {output_path}")
    print("\n归一后前 5 行预览：")
    print(normalized_df.head())
