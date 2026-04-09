# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/05 11:08
IDE       :PyCharm
作者      :董宏升

第三周：解释链工具层

该模块目标是把第二周结果层事实和第三周规则层依据拼成完整解释。

可以理解为三层：
1. 结果事实层（来自第二周异常明细 / analysis_tools 结果）
    - 是否疑似低价异常
    - 低价规则来源
    - 是否跨平台价格差异
    - 是否规格识别风险
    - 异常原因
    - 以及相关数值字段

2.规则依据层（来自本周三 retrieval_tools）
    - 搜到哪些规则片段
    - 当前主要命中了什么规则主题
    - 最相关证据来自哪份文档哪一节

3.复核建议层
    - 根据异常类型给一条可执行建议

注意：
该文件不是重新判断异常
而是在“解释第二周已经判断出的异常”。
所以这里必须尊重结果层，尤其低价解释必须先看“低价规则来源”。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from typing import Any
from app.tools.retrieval_tools import build_rule_search_summary, search_rules

"""1. 小工具"""


# 任意值稳妥转成字符串
def safe_text(value: Any) -> str:
    """把任意值稳妥转成字符串。"""
    if value is None:
        return ""
    return str(value)


# 稳妥把值转为布尔。
def safe_bool(value: Any) -> bool:
    """
    此处兼容：
    - True / False
    - "true" / "false"
    - 1 / 0
    - yes / no
    - NaN / None
    """
    if value is True:
        return True
    if value is False:
        return False

    text = safe_text(value).strip().lower()
    return text in {"true", "1", "yes"}


# 尝试将值转为 float，失败返回 None
def safe_float(value: Any) -> float | None:
    try:
        text = safe_text(value).strip()
        if text == "" or text.lower() == "nan":
            return None
        return float(text)
    except Exception:
        return None


# 把数字格式化为更合适展示的文本
def format_num(value: Any, digits: int = 2) -> str:
    number = safe_float(value)
    if number is None:
        return "未知"
    return f"{number:.{digits}f}"


# 从一组候选字段里去第一个非空值。
def pick_first_nonempty(row: dict[str, Any], keys: list[str]) -> Any:
    """
    目的为我当前项目中，虽然结果层主口径已经是中文列，但是为了兼容中间过程或未来接口输入，工具层最好稍微抗一点字段变化。
    """
    for key in keys:
        if key not in row:
            continue

        value = row.get(key)

        if value is None:
            continue

        # False 和 0 都是有效值，不能当空
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            text = safe_text(value).strip().lower()
            if text == "nan":
                continue
            return value

        text = safe_text(value).strip()
        if text == "" or text.lower() == "nan":
            continue

        return value

    return None


"""2.从结果层抽事实"""


def extract_result_facts(row: dict[str, Any]) -> dict[str, Any]:
    """
    从第二周结果层里抽取解释所需的核心事实字段。这里重点围绕目前已经稳定下来的中文列进行取值。
    """
    return {
        # 样本身份
        "brand": pick_first_nonempty(row, ["标准化品牌", "normalized_brand"]),
        "spec": pick_first_nonempty(row, ["规范化规格", "normalized_spec"]),
        "platform": pick_first_nonempty(row, ["干净平台", "normalized_platform"]),
        "price": pick_first_nonempty(row, ["干净价格", "price"]),
        "title": pick_first_nonempty(row, ["干净标题", "clean_title", "商品标题"]),

        # 低价相关
        "is_low_price": pick_first_nonempty(row, ["是否疑似异常低价", "is_low_price_anomaly"]),
        "low_price_rule_source": pick_first_nonempty(row, ["低价规则来源", "low_price_rule_source"]),
        "explicit_low_price_threshold": pick_first_nonempty(row, ["显式低价阈值", "explicit_low_price_threshold"]),
        "group_avg_price": pick_first_nonempty(row, ["组内均价", "group_avg_price"]),
        "price_vs_group_mean_ratio": pick_first_nonempty(row, ["当前价格/组均价比", "price_vs_group_mean_ratio"]),

        # 跨平台相关
        "is_cross_platform": pick_first_nonempty(row, ["是否跨平台价差异常", "is_cross_platform_anomaly"]),
        "group_min_price": pick_first_nonempty(row, ["组内最低价", "group_min_price"]),
        "group_max_price": pick_first_nonempty(row, ["组内最高价", "group_max_price"]),
        "cross_platform_gap_ratio": pick_first_nonempty(row, ["跨平台价差比例", "cross_platform_gap_ratio"]),

        # 规格风险相关
        "is_spec_risk": pick_first_nonempty(row, ["是否规格识别风险", "is_spec_risk"]),
        "title_spec_hint": pick_first_nonempty(row, ["标题规范提示", "title_spec_hint"]),
        "clean_spec": pick_first_nonempty(row, ["干净规格", "clean_spec"]),
        "spec_source": pick_first_nonempty(row, ["规范来源", "spec_source"]),

        # 结果层摘要
        "anomaly_reason": pick_first_nonempty(row, ["异常原因", "anomaly_reason"]),
    }


"""3. 规则查询问题生成"""


def build_rule_query_from_facts(facts: dict[str, Any]) -> str:
    """
    根据结果层事实，生成更适合规则检索的查询问题。

    为什么不直接把“商品标题 + 一堆数值”扔给 search_rules?
    因为第三周规则检索要找的是“规则依据”，不是搜索具体商品记录。所以把问题抽象成规则层更能理解的问法。
    """
    is_low_price = safe_bool(facts.get("is_low_price"))
    is_cross_platform = safe_bool(facts.get("is_cross_platform"))
    is_spec_risk = safe_bool(facts.get("is_spec_risk"))

    if is_low_price:
        rule_source = safe_text(facts.get("low_price_rule_source")).strip()

        if rule_source == "explicit_rule":
            return "为什么这个商品会被判成疑似异常低价？显式阈值规则是怎么定义的？"
        if rule_source == "stat_rule":
            return "为什么这个商品会被判成疑似异常低价？统计低价规则是怎么定义的？"
        if rule_source == "both":
            return "为什么这个商品会被判成疑似异常低价？同时命中显式阈值和统计规则是什么意思？"

        return "为什么这个商品会被判成疑似异常低价？"

    if is_cross_platform:
        return "为什么这个商品会被判成跨平台价差异常？"

    if is_spec_risk:
        return "为什么这个商品会被判成规格识别风险？如果标题不完整，规则上该怎么处理？"

    return "这个商品的异常规则依据是什么？"


def should_use_generated_rule_query(user_question: str, facts: dict[str, Any]) -> bool:
    """
    判断当前是否应该优先使用“根据 facts 自动生成的规则问句”。

    为什么要加这个函数？
    因为有些用户问题太泛，比如：
    - 为什么这个商品会被判成高风险？
    - 为什么它异常？
    - 这个商品为什么有问题？

    这种问法更适合先根据结果层事实，把问题改写成：
    - 为什么会被判成疑似异常低价？统计低价规则是怎么定义的？
    - 为什么会被判成跨平台价差异常？
    - 为什么会被判成规格识别风险？

    这样去检索规则，会比直接拿“高风险”这种泛词去搜更准。
    """
    question = safe_text(user_question).strip()
    if not question:
        return True

    q = question.lower()

    # 这些词说明用户已经问得比较具体了
    # 这种情况下，保留用户原问题更合适
    specific_keywords = [
        "低价",
        "跨平台",
        "价差",
        "规格",
        "标题不完整",
        "显式阈值",
        "统计规则",
        "规则来源",
        "复核",
    ]

    if any(keyword in q for keyword in specific_keywords):
        return False

    # 这些词说明用户是在“泛解释”
    # 比如“高风险”“为什么这个商品异常”
    generic_keywords = [
        "高风险",
        "异常",
        "有问题",
        "为什么这个商品",
        "为什么该商品",
    ]

    has_generic_signal = any(keyword in q for keyword in generic_keywords)

    # 只要结果层里已经明确有某类异常，
    # 且用户问题又比较泛，就优先用自动生成问句
    has_fact_signal = (
            safe_bool(facts.get("is_low_price"))
            or safe_bool(facts.get("is_cross_platform"))
            or safe_bool(facts.get("is_spec_risk"))
    )

    return has_generic_signal and has_fact_signal


""" 4. 结果事实解释"""


def build_identity_text(facts: dict[str, Any]) -> str:
    """拼接样本身份文本。"""
    brand = safe_text(facts.get("brand")).strip()
    spec = safe_text(facts.get("spec")).strip()
    platform = safe_text(facts.get("platform")).strip()

    bits = [item for item in [brand, spec, platform] if item]
    if not bits:
        return "当前样本"

    return f"当前样本为“{' / '.join(bits)}”"


def build_fact_explanation(facts: dict[str, Any]) -> str:
    """
    先用第二周结果层字段，拼成发生了什么。
    此处是解释链最重要的部分，因为规则层只能补依据，不能替代结果层事实。
    """
    parts: list[str] = []

    identity_text = build_identity_text(facts)
    price_text = format_num(facts.get("price"))
    parts.append(f"{identity_text}，当前价格为 {price_text}。")

    # 1）低价异常：必须先看低价规则来源
    if safe_bool(facts.get("is_low_price")):
        rule_source = safe_text(facts.get("low_price_rule_source")).strip()
        avg_price = format_num(facts.get("group_avg_price"))
        ratio = format_num(facts.get("price_vs_group_mean_ratio"))
        threshold = format_num(facts.get("explicit_low_price_threshold"))

        if rule_source == "explicit_rule":
            parts.append(
                f"结果层显示该样本命中了显式低价规则，显式阈值为 {threshold}，因此被判为疑似异常低价。"
            )
        elif rule_source == "stat_rule":
            parts.append(
                f"结果层显示该样本命中了统计低价规则，组内均价为 {avg_price}，当前价格/组均价比为 {ratio}，因此被判为疑似异常低价。"
            )
        elif rule_source == "both":
            parts.append(
                f"结果层显示该样本同时命中显式阈值和统计低价规则，显式阈值为 {threshold}，组内均价为 {avg_price}，当前价格/组均价比为 {ratio}。"
            )
        else:
            parts.append("结果层显示该样本被标记为疑似异常低价。")

    # 2）跨平台价差异常
    if safe_bool(facts.get("is_cross_platform")):
        min_price = format_num(facts.get("group_min_price"))
        max_price = format_num(facts.get("group_max_price"))
        gap_ratio = format_num(facts.get("cross_platform_gap_ratio"))

        parts.append(
            f"结果层同时显示该样本命中了跨平台价差异常，组内最低价为 {min_price}，组内最高价为 {max_price}，跨平台价差比例为 {gap_ratio}。"
        )

    # 3）规格识别风险
    if safe_bool(facts.get("is_spec_risk")):
        clean_spec = safe_text(facts.get("clean_spec")).strip()
        title_spec_hint = safe_text(facts.get("title_spec_hint")).strip()

        if clean_spec and title_spec_hint:
            parts.append(
                f"结果层还显示该样本存在规格识别风险，规格列为“{clean_spec}”，标题规格提示为“{title_spec_hint}”。"
            )
        else:
            parts.append("结果层还显示该样本存在规格识别风险。")

    anomaly_reason = safe_text(facts.get("anomaly_reason")).strip()
    if anomaly_reason:
        parts.append(f"结果层摘要为：{anomaly_reason}")

    return " ".join(parts).strip()


"""5. 规则层摘要"""


def choose_primary_evidence(rule_search: dict[str, Any]) -> dict[str, Any] | None:
    """
    选择“主依据”证据。

    优先级：
    1. 非 FAQ 文档
    2. 如果全是 FAQ，再退回第一条
    """
    evidences = rule_search.get("evidences", []) or []
    if not evidences:
        return None

    for evidence in evidences:
        if safe_text(evidence.get("doc_id")) != "faq":
            return evidence

    return evidences[0]


def build_rule_evidence_summary(rule_search: dict[str, Any]) -> str:
    """
    构造更适合解释链的规则层摘要。

    这里优先引用主规则文档，而不是默认引用 FAQ。
    """
    ok = rule_search.get("ok", False)
    if not ok:
        return safe_text(rule_search.get("message", "规则检索失败。"))

    topic = safe_text(rule_search.get("topic")).strip() or "通用规则"
    primary = choose_primary_evidence(rule_search)

    if primary is None:
        return f"该问题当前暂未检索到高相关的“{topic}”规则片段。"

    doc_title = safe_text(primary.get("doc_title")).strip()
    section_title = safe_text(primary.get("section_title")).strip()

    return (
        f"规则层检索显示，该问题当前主要命中“{topic}”相关规则，"
        f"主要依据来自《{doc_title}》的《{section_title}》章节。"
    )


"""6. 复核建议"""


def build_review_suggestion(facts: dict[str, Any]) -> str:
    """
    根据异常类型，给一条简短复核建议
    我这里先做规则型建议，后面如果我想更细可以迭代。
    """
    suggestions: list[str] = []

    if safe_bool(facts.get("is_low_price")):
        suggestions.append("建议优先复核该价格是否为券后价、活动价、补贴价，或是否存在临期清仓、组合装等特殊口径。")

    if safe_bool(facts.get("is_cross_platform")):
        suggestions.append("建议进一步核对最低价平台是否存在专项活动、抓取口径差异或规格误配。")

    if safe_bool(facts.get("is_spec_risk")):
        suggestions.append("建议重点复核标题中的规格提示、规格列填写以及是否存在组合装、赠品装、促销装等特殊写法。")

    if not suggestions:
        return "建议结合原始商品标题、规格、价格字段做进一步人工复核。"

    return " ".join(suggestions).strip()


"""7.最终解释拼接"""


def build_final_explanation(
        fact_explanation: str,
        rule_summary: str,
        review_suggestion: str,
) -> str:
    """把三段解释拼成最终输出。"""
    parts = [
        fact_explanation.strip(),
        rule_summary.strip(),
        review_suggestion.strip(),
    ]
    parts = [part for part in parts if part]
    return " ".join(parts)


"""8. 对外主入口：解释单条异常样本"""


# 给单条异常样本生成解释结果
def explain_anomaly_row(
        row: dict[str, Any],
        user_question: str | None = None,
        top_k: int = 3,
) -> dict[str, Any]:
    """
    :param row:一条异常样本记录（可以是 DataFrame.to_dict后的一行）
    :param user_question:可选，用户原始问题；不传则自动生成规则查询问句。
    :param top_k:检索几条规则证据

    输出：
        - facts:结果层事实
        - rule_search：规则检索结果
        - fact_explanation：结果层解释
        - rule_summary：规则层摘要
        - review_suggestion：复核建议
        - final_explanation: 最终完整解释
    """
    # 先从第二周结果层里抽核心事实
    facts = extract_result_facts(row)

    # 用户原始问题
    raw_question = safe_text(user_question).strip()

    # 根据结果层事实自动生成一个“更适合规则检索”的问题
    generated_rule_query = build_rule_query_from_facts(facts)

    # 规则：
    # 1. 如果用户没传问题，直接用自动生成问句
    # 2. 如果用户问题太泛（比如“为什么高风险”），也优先用自动生成问句
    # 3. 如果用户问题已经很具体，就保留用户原问题
    if not raw_question:
        rule_query = generated_rule_query
    elif should_use_generated_rule_query(raw_question, facts):
        rule_query = generated_rule_query
    else:
        rule_query = raw_question

    # 去规则层检索证据
    rule_search = search_rules(query=rule_query, top_k=top_k)

    # 结果层解释：先讲发生了什么
    fact_explanation = build_fact_explanation(facts)

    # 规则层摘要：再讲依据来自哪里
    rule_summary = build_rule_evidence_summary(rule_search)

    # 复核建议：最后补一个可执行建议
    review_suggestion = build_review_suggestion(facts)

    # 拼成最终解释文本
    final_explanation = build_final_explanation(
        fact_explanation=fact_explanation,
        rule_summary=rule_summary,
        review_suggestion=review_suggestion,
    )

    return {
        "facts": facts,
        "rule_query": rule_query,
        "rule_search": rule_search,
        "fact_explanation": fact_explanation,
        "rule_summary": rule_summary,
        "review_suggestion": review_suggestion,
        "final_explanation": final_explanation,
    }


# -----------------------------------
# 9. 本地调试示例
# -----------------------------------


if __name__ == "__main__":
    # 这条 demo_row 故意做成“低价 + 跨平台”双异常样本，
    # 方便你看解释链有没有把两类异常都讲出来。
    demo_row = {
        "标准化品牌": "同仁堂",
        "规范化规格": "9袋/盒",
        "干净平台": "拼多多",
        "干净价格": 20.33,

        "是否疑似异常低价": True,
        "低价规则来源": "stat_rule",
        "组内均价": 28.04,
        "当前价格/组均价比": 0.73,

        "是否跨平台价差异常": True,
        "组内最低价": 20.33,
        "组内最高价": 30.80,
        "跨平台价差比例": 0.34,

        "是否规格识别风险": False,

        "异常原因": "疑似异常低价：当前价格低于同品牌同规格均价，均价=28.04，当前/均价=0.73；跨平台价差过大：最低价=20.33，最高价=30.80，价差比例=0.34",
    }

    payload = explain_anomaly_row(demo_row)

    print("规则查询问题：")
    print(payload["rule_query"])

    print("\n抽取到的结果层事实：")
    print(payload["facts"])

    print("\n结果层解释：")
    print(payload["fact_explanation"])

    print("\n规则层摘要：")
    print(payload["rule_summary"])

    print("\n复核建议：")
    print(payload["review_suggestion"])

    print("\n最终解释：")
    print(payload["final_explanation"])

# if __name__ == "__main__":
#     demo_cases = [
#         {
#             "case_id": "B-02",
#             "case_name": "显式阈值低价解释",
#             "row": {
#                 "标准化品牌": "鸿茅",
#                 "规范化规格": "500ml",
#                 "干净平台": "京东",
#                 "干净价格": 168.00,
#
#                 "是否疑似异常低价": True,
#                 "低价规则来源": "explicit_rule",
#                 "显式低价阈值": 180.00,
#                 "组内均价": 198.50,
#                 "当前价格/组均价比": 0.85,
#
#                 "是否跨平台价差异常": False,
#                 "组内最低价": 168.00,
#                 "组内最高价": 205.00,
#                 "跨平台价差比例": 0.18,
#
#                 "是否规格识别风险": False,
#
#                 "异常原因": "疑似异常低价：命中显式阈值规则，阈值<180.00，当前价格=168.00",
#             },
#         },
#         {
#             "case_id": "B-04",
#             "case_name": "规格风险解释",
#             "row": {
#                 "标准化品牌": "鸿茅",
#                 "规范化规格": "250ml",
#                 "干净平台": "淘宝",
#                 "干净价格": 92.00,
#                 "干净规格": "250ml",
#                 "标题规范提示": "500ml",
#                 "规范来源": "spec_column",
#
#                 "是否疑似异常低价": False,
#                 "低价规则来源": "",
#                 "显式低价阈值": None,
#                 "组内均价": 95.00,
#                 "当前价格/组均价比": 0.97,
#
#                 "是否跨平台价差异常": False,
#                 "组内最低价": 90.00,
#                 "组内最高价": 98.00,
#                 "跨平台价差比例": 0.08,
#
#                 "是否规格识别风险": True,
#
#                 "异常原因": "规格识别风险：规格列=250ml，标题规格=500ml",
#             },
#         },
#     ]
#
#     for case in demo_cases:
#         print("\n" + "#" * 100)
#         print(f"验收样例：{case['case_id']} - {case['case_name']}")
#
#         payload = explain_anomaly_row(case["row"])
#
#         print("规则查询问题：")
#         print(payload["rule_query"])
#
#         print("\n抽取到的结果层事实：")
#         print(payload["facts"])
#
#         print("\n结果层解释：")
#         print(payload["fact_explanation"])
#
#         print("\n规则层摘要：")
#         print(payload["rule_summary"])
#
#         print("\n复核建议：")
#         print(payload["review_suggestion"])
#
#         print("\n最终解释：")
#         print(payload["final_explanation"])
