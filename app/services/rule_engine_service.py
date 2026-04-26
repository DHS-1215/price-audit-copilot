# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/22 21:36
IDE       :PyCharm
作者      :董宏升
规则引擎服务（V1）
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pandas as pd

from app.models.rule_definition import RuleDefinition

# 正式规则编码
RULE_LOW_PRICE_EXPLICIT = "LOW_PRICE_EXPLICIT"
RULE_LOW_PRICE_STAT = "LOW_PRICE_STAT"
RULE_CROSS_PLATFORM_GAP = "CROSS_PLATFORM_GAP"
RULE_SPEC_RISK = "SPEC_RISK"

ANOMALY_LOW_PRICE = "low_price"
ANOMALY_CROSS_PLATFORM_GAP = "cross_platform_gap"
ANOMALY_SPEC_RISK = "spec_risk"

# 为兼容旧 preview / 新 product_clean DataFrame，先做一层列名映射
COLUMN_ALIASES: dict[str, list[str]] = {
    "clean_id": ["clean_id", "id"],
    "clean_title": ["clean_title", "干净标题"],
    "clean_spec": ["clean_spec", "干净规格"],
    "normalized_brand": ["normalized_brand", "标准化品牌"],
    "normalized_spec": ["normalized_spec", "规范化规格"],
    "price": ["price", "干净价格"],
    "normalized_platform": ["normalized_platform", "干净平台"],
    "title_spec_hint": ["title_spec_hint", "标题规范提示"],
    "title_spec_mismatch_flag": ["title_spec_mismatch_flag", "标题规格不匹配标志"],
    "missing_normalized_spec_flag": [
        "missing_normalized_spec_flag",
        "缺少规范化规范标志",
        "缺少规范化规格标志",
    ],
}


@dataclass
class RuleHitDraft:
    anomaly_type: str
    rule_code: str
    rule_version: str
    rule_definition_id: int | None
    is_hit: bool
    input_snapshot_json: dict[str, Any] | None = None
    computed_value_json: dict[str, Any] | None = None
    threshold_snapshot_json: dict[str, Any] | None = None
    hit_message: str | None = None
    hit_order: int = 1


@dataclass
class AuditResultDraft:
    clean_id: int
    anomaly_type: str
    is_hit: bool
    hit_rule_code: str | None = None
    hit_rule_version: str | None = None
    rule_definition_id: int | None = None

    explicit_low_price_threshold: Decimal | None = None
    group_avg_price: Decimal | None = None
    price_to_group_avg_ratio: Decimal | None = None
    low_price_rule_source: str | None = None

    reason_text: str | None = None
    input_snapshot_json: dict[str, Any] | None = None

    rule_hits: list[RuleHitDraft] = field(default_factory=list)


class RuleEngineService:
    """
    规则引擎服务：
    - 接收规范化后的 DataFrame
    - 计算组统计
    - 评估低价 / 跨平台价差 / 规格风险
    - 返回 audit_result 草稿 + rule_hit 草稿
    """

    REQUIRED_COLUMNS = [
        "clean_id",
        "normalized_brand",
        "normalized_spec",
        "price",
        "normalized_platform",
        "clean_spec",
        "title_spec_hint",
        "title_spec_mismatch_flag",
        "missing_normalized_spec_flag",
    ]

    def __init__(self, rule_definitions: list[RuleDefinition]):
        self.rule_map: dict[str, RuleDefinition] = {
            item.rule_code: item for item in rule_definitions if item.enabled
        }

    # ==========
    # 对外主入口
    # ==========

    def evaluate_dataframe(self, df: pd.DataFrame) -> list[AuditResultDraft]:
        frame = self.prepare_analysis_frame(df)

        drafts: list[AuditResultDraft] = []
        for _, row in frame.iterrows():
            clean_id = int(row["clean_id"])

            drafts.append(self.evaluate_low_price(row=row, clean_id=clean_id))
            drafts.append(self.evaluate_cross_platform_gap(row=row, clean_id=clean_id))
            drafts.append(self.evaluate_spec_risk(row=row, clean_id=clean_id))

        return drafts

    # ==========
    # 前置准备
    # ==========

    def prepare_analysis_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        result = self.standardize_columns(df)
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in result.columns]
        if missing_cols:
            raise ValueError(f"规则引擎缺少必要列：{missing_cols}")

        result["price"] = pd.to_numeric(result["price"], errors="coerce")
        result["title_spec_mismatch_flag"] = result["title_spec_mismatch_flag"].apply(self._safe_to_bool)
        result["missing_normalized_spec_flag"] = result["missing_normalized_spec_flag"].apply(self._safe_to_bool)

        # 统计底座：同品牌 + 同规格
        group_cols = ["normalized_brand", "normalized_spec"]

        stats = (
            result.groupby(group_cols, dropna=False)
            .agg(
                group_sample_count=("price", lambda s: s.notna().sum()),
                group_distinct_platform_count=(
                    "normalized_platform", lambda s: s.dropna().astype(str).str.strip().nunique()),
                group_avg_price=("price", "mean"),
                group_min_price=("price", "min"),
                group_max_price=("price", "max"),
            )
            .reset_index()
        )

        result = result.merge(stats, on=group_cols, how="left")

        result["price_to_group_avg_ratio"] = result.apply(
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

    def standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        result.columns = [str(col).replace("\ufeff", "").strip() for col in result.columns]

        for canonical_name, aliases in COLUMN_ALIASES.items():
            actual = self._find_first_existing_column(result, aliases)
            if actual is not None and canonical_name not in result.columns:
                result[canonical_name] = result[actual]

        return result

    # ==========
    # 三类异常判定
    # ==========

    def evaluate_low_price(self, row: pd.Series, clean_id: int) -> AuditResultDraft:
        explicit_rule = self.rule_map.get(RULE_LOW_PRICE_EXPLICIT)
        stat_rule = self.rule_map.get(RULE_LOW_PRICE_STAT)

        brand = self._to_str(row.get("normalized_brand"))
        spec = self._to_str(row.get("normalized_spec"))
        platform = self._to_str(row.get("normalized_platform"))

        current_price = self._to_decimal(row.get("price"))
        group_avg_price = self._to_decimal(row.get("group_avg_price"))
        ratio = self._to_decimal(row.get("price_to_group_avg_ratio"))
        group_sample_count = int(row.get("group_sample_count") or 0)

        explicit_threshold = self._find_explicit_threshold(
            brand=brand,
            spec=spec,
            rule=explicit_rule,
        )

        stat_min_group_size = self._get_int_config(
            stat_rule,
            "min_group_size",
            default=3,
        )
        stat_ratio_threshold = self._get_decimal_config(
            stat_rule,
            "ratio_threshold",
            default=Decimal("0.80"),
        )

        is_explicit_hit = (
                current_price is not None
                and explicit_threshold is not None
                and current_price < explicit_threshold
        )

        is_stat_hit = (
                current_price is not None
                and group_avg_price is not None
                and group_sample_count >= stat_min_group_size
                and current_price < (group_avg_price * stat_ratio_threshold)
        )

        low_price_rule_source = self._get_low_price_rule_source(
            is_explicit_hit=is_explicit_hit,
            is_stat_hit=is_stat_hit,
        )
        is_hit = is_explicit_hit or is_stat_hit

        if current_price is not None and explicit_threshold is not None:
            explicit_hit_message = (
                f"当前价格={current_price}，显式阈值={explicit_threshold}"
            )
        elif current_price is not None:
            explicit_hit_message = (
                f"当前价格={current_price}，未配置匹配的显式阈值"
            )
        else:
            explicit_hit_message = "当前价格缺失，无法判断显式低价规则"

        stat_hit_message = None
        if current_price is not None and group_avg_price is not None and ratio is not None:
            stat_hit_message = (
                f"当前价格={current_price}，组均价={group_avg_price}，"
                f"当前/均价={ratio}，阈值={stat_ratio_threshold}"
            )

        rule_hits: list[RuleHitDraft] = []

        if explicit_rule is not None:
            rule_hits.append(
                RuleHitDraft(
                    anomaly_type=ANOMALY_LOW_PRICE,
                    rule_code=explicit_rule.rule_code,
                    rule_version=explicit_rule.version,
                    rule_definition_id=explicit_rule.id,
                    is_hit=is_explicit_hit,
                    input_snapshot_json={
                        "clean_id": clean_id,
                        "brand": brand,
                        "spec": spec,
                        "platform": platform,
                        "price": self._json_number(current_price),
                    },
                    computed_value_json={
                        "matched_explicit_threshold": self._json_number(explicit_threshold),
                    },
                    threshold_snapshot_json=self._json_obj(explicit_rule.threshold_config_json),
                    hit_message=(
                        f"命中显式低价规则：{explicit_hit_message}"
                        if is_explicit_hit
                        else f"未命中显式低价规则：{explicit_hit_message}"
                    ),
                    hit_order=1,
                )
            )

        if stat_rule is not None:
            rule_hits.append(
                RuleHitDraft(
                    anomaly_type=ANOMALY_LOW_PRICE,
                    rule_code=stat_rule.rule_code,
                    rule_version=stat_rule.version,
                    rule_definition_id=stat_rule.id,
                    is_hit=is_stat_hit,
                    input_snapshot_json={
                        "clean_id": clean_id,
                        "brand": brand,
                        "spec": spec,
                        "platform": platform,
                        "price": self._json_number(current_price),
                        "group_sample_count": group_sample_count,
                    },
                    computed_value_json={
                        "group_avg_price": self._json_number(group_avg_price),
                        "price_to_group_avg_ratio": self._json_number(ratio),
                    },
                    threshold_snapshot_json={
                        "min_group_size": stat_min_group_size,
                        "ratio_threshold": self._json_number(stat_ratio_threshold),
                    },
                    hit_message=(
                        f"命中统计低价规则：{stat_hit_message}"
                        if is_stat_hit
                        else f"未命中统计低价规则：{stat_hit_message}"
                    ),
                    hit_order=2,
                )
            )

        primary_rule = self._pick_primary_low_price_rule(
            explicit_rule=explicit_rule,
            stat_rule=stat_rule,
            is_explicit_hit=is_explicit_hit,
            is_stat_hit=is_stat_hit,
        )

        return AuditResultDraft(
            clean_id=clean_id,
            anomaly_type=ANOMALY_LOW_PRICE,
            is_hit=is_hit,
            hit_rule_code=primary_rule.rule_code if primary_rule is not None and is_hit else None,
            hit_rule_version=primary_rule.version if primary_rule is not None and is_hit else None,
            rule_definition_id=primary_rule.id if primary_rule is not None and is_hit else None,
            explicit_low_price_threshold=explicit_threshold,
            group_avg_price=group_avg_price,
            price_to_group_avg_ratio=ratio,
            low_price_rule_source=low_price_rule_source if is_hit else None,
            reason_text=self._build_low_price_reason(
                is_explicit_hit=is_explicit_hit,
                is_stat_hit=is_stat_hit,
                current_price=current_price,
                explicit_threshold=explicit_threshold,
                group_avg_price=group_avg_price,
                ratio=ratio,
            ),
            input_snapshot_json={
                "clean_id": clean_id,
                "brand": brand,
                "spec": spec,
                "platform": platform,
                "price": self._json_number(current_price),
                "group_sample_count": group_sample_count,
            },
            rule_hits=rule_hits,
        )

    def evaluate_cross_platform_gap(self, row: pd.Series, clean_id: int) -> AuditResultDraft:
        rule = self.rule_map.get(RULE_CROSS_PLATFORM_GAP)

        brand = self._to_str(row.get("normalized_brand"))
        spec = self._to_str(row.get("normalized_spec"))
        platform = self._to_str(row.get("normalized_platform"))

        current_price = self._to_decimal(row.get("price"))
        group_min_price = self._to_decimal(row.get("group_min_price"))
        group_max_price = self._to_decimal(row.get("group_max_price"))
        gap_ratio = self._to_decimal(row.get("cross_platform_gap_ratio"))
        distinct_platform_count = int(row.get("group_distinct_platform_count") or 0)

        min_distinct_platforms = self._get_int_config(
            rule,
            "min_distinct_platforms",
            default=2,
        )
        gap_ratio_threshold = self._get_decimal_config(
            rule,
            "gap_ratio_threshold",
            default=Decimal("0.25"),
        )
        flag_only_lowest_price = self._get_bool_config(
            rule,
            "flag_only_lowest_price",
            default=True,
        )

        is_group_gap_hit = (
                current_price is not None
                and group_min_price is not None
                and group_max_price is not None
                and gap_ratio is not None
                and distinct_platform_count >= min_distinct_platforms
                and gap_ratio >= gap_ratio_threshold
        )

        is_current_row_lowest = (
                current_price is not None
                and group_min_price is not None
                and current_price == group_min_price
        )

        is_hit = (
            is_group_gap_hit and is_current_row_lowest
            if flag_only_lowest_price
            else is_group_gap_hit
        )

        rule_hits: list[RuleHitDraft] = []
        if rule is not None:
            rule_hits.append(
                RuleHitDraft(
                    anomaly_type=ANOMALY_CROSS_PLATFORM_GAP,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    rule_definition_id=rule.id,
                    is_hit=is_hit,
                    input_snapshot_json={
                        "clean_id": clean_id,
                        "brand": brand,
                        "spec": spec,
                        "platform": platform,
                        "price": self._json_number(current_price),
                        "distinct_platform_count": distinct_platform_count,
                    },
                    computed_value_json={
                        "group_min_price": self._json_number(group_min_price),
                        "group_max_price": self._json_number(group_max_price),
                        "cross_platform_gap_ratio": self._json_number(gap_ratio),
                        "is_group_gap_hit": is_group_gap_hit,
                        "is_current_row_lowest": is_current_row_lowest,
                    },
                    threshold_snapshot_json={
                        "min_distinct_platforms": min_distinct_platforms,
                        "gap_ratio_threshold": self._json_number(gap_ratio_threshold),
                        "flag_only_lowest_price": flag_only_lowest_price,
                    },
                    hit_message=(
                        f"命中跨平台价差规则：最低价={group_min_price}，最高价={group_max_price}，"
                        f"价差比例={gap_ratio}"
                        if is_hit
                        else f"未命中跨平台价差规则：最低价={group_min_price}，最高价={group_max_price}，"
                             f"价差比例={gap_ratio}"
                    ),
                    hit_order=1,
                )
            )

        return AuditResultDraft(
            clean_id=clean_id,
            anomaly_type=ANOMALY_CROSS_PLATFORM_GAP,
            is_hit=is_hit,
            hit_rule_code=rule.rule_code if rule is not None and is_hit else None,
            hit_rule_version=rule.version if rule is not None and is_hit else None,
            rule_definition_id=rule.id if rule is not None and is_hit else None,
            reason_text=(
                f"跨平台价差过大：最低价={group_min_price}，最高价={group_max_price}，价差比例={gap_ratio}"
                if is_hit
                else None
            ),
            input_snapshot_json={
                "clean_id": clean_id,
                "brand": brand,
                "spec": spec,
                "platform": platform,
                "price": self._json_number(current_price),
                "distinct_platform_count": distinct_platform_count,
            },
            rule_hits=rule_hits,
        )

    def evaluate_spec_risk(self, row: pd.Series, clean_id: int) -> AuditResultDraft:
        rule = self.rule_map.get(RULE_SPEC_RISK)

        clean_title = self._to_str(row.get("clean_title"))
        clean_spec = self._to_str(row.get("clean_spec"))
        normalized_spec = self._to_str(row.get("normalized_spec"))
        title_spec_hint = self._to_str(row.get("title_spec_hint"))

        title_mismatch = self._safe_to_bool(row.get("title_spec_mismatch_flag"))
        missing_normalized_spec = self._safe_to_bool(row.get("missing_normalized_spec_flag"))

        enabled_conditions = self._get_list_config(
            rule,
            "conditions",
            default=["title_spec_mismatch", "missing_normalized_spec"],
        )

        triggered_conditions: list[str] = []
        if "title_spec_mismatch" in enabled_conditions and title_mismatch:
            triggered_conditions.append("title_spec_mismatch")
        if "missing_normalized_spec" in enabled_conditions and missing_normalized_spec:
            triggered_conditions.append("missing_normalized_spec")

        is_hit = len(triggered_conditions) > 0

        rule_hits: list[RuleHitDraft] = []
        if rule is not None:
            rule_hits.append(
                RuleHitDraft(
                    anomaly_type=ANOMALY_SPEC_RISK,
                    rule_code=rule.rule_code,
                    rule_version=rule.version,
                    rule_definition_id=rule.id,
                    is_hit=is_hit,
                    input_snapshot_json={
                        "clean_id": clean_id,
                        "clean_title": clean_title,
                        "clean_spec": clean_spec,
                        "title_spec_hint": title_spec_hint,
                        "normalized_spec": normalized_spec,
                    },
                    computed_value_json={
                        "title_spec_mismatch": title_mismatch,
                        "missing_normalized_spec": missing_normalized_spec,
                        "triggered_conditions": triggered_conditions,
                    },
                    threshold_snapshot_json={
                        "conditions": enabled_conditions,
                    },
                    hit_message=(
                        f"命中规格识别风险规则：{','.join(triggered_conditions)}"
                        if is_hit
                        else "未命中规格识别风险规则"
                    ),
                    hit_order=1,
                )
            )

        return AuditResultDraft(
            clean_id=clean_id,
            anomaly_type=ANOMALY_SPEC_RISK,
            is_hit=is_hit,
            hit_rule_code=rule.rule_code if rule is not None and is_hit else None,
            hit_rule_version=rule.version if rule is not None and is_hit else None,
            rule_definition_id=rule.id if rule is not None and is_hit else None,
            reason_text=self._build_spec_risk_reason(
                title_mismatch=title_mismatch,
                missing_normalized_spec=missing_normalized_spec,
                clean_spec=clean_spec,
                title_spec_hint=title_spec_hint,
            ),
            input_snapshot_json={
                "clean_id": clean_id,
                "clean_title": clean_title,
                "clean_spec": clean_spec,
                "title_spec_hint": title_spec_hint,
                "normalized_spec": normalized_spec,
            },
            rule_hits=rule_hits,
        )

    # ==========
    # 规则配置读取
    # ==========

    def _find_explicit_threshold(
            self,
            brand: str,
            spec: str,
            rule: RuleDefinition | None,
    ) -> Decimal | None:
        if rule is None:
            return None

        config = rule.threshold_config_json or {}
        rules = config.get("rules", [])

        for item in rules:
            cfg_brand = self._to_str(item.get("brand"))
            cfg_spec = self._to_str(item.get("spec"))
            if cfg_brand == brand and cfg_spec == spec:
                return self._to_decimal(item.get("threshold"))

        return None

    def _get_int_config(
            self,
            rule: RuleDefinition | None,
            key: str,
            default: int,
    ) -> int:
        if rule is None or not rule.threshold_config_json:
            return default
        value = rule.threshold_config_json.get(key, default)
        try:
            return int(value)
        except Exception:
            return default

    def _get_bool_config(
            self,
            rule: RuleDefinition | None,
            key: str,
            default: bool,
    ) -> bool:
        if rule is None or not rule.threshold_config_json:
            return default
        return self._safe_to_bool(rule.threshold_config_json.get(key, default))

    def _get_decimal_config(
            self,
            rule: RuleDefinition | None,
            key: str,
            default: Decimal,
    ) -> Decimal:
        if rule is None or not rule.threshold_config_json:
            return default
        value = self._to_decimal(rule.threshold_config_json.get(key))
        return value if value is not None else default

    def _get_list_config(
            self,
            rule: RuleDefinition | None,
            key: str,
            default: list[str],
    ) -> list[str]:
        if rule is None or not rule.threshold_config_json:
            return default
        value = rule.threshold_config_json.get(key, default)
        return value if isinstance(value, list) else default

    # ==========
    # 原因文本
    # ==========

    def _build_low_price_reason(
            self,
            is_explicit_hit: bool,
            is_stat_hit: bool,
            current_price: Decimal | None,
            explicit_threshold: Decimal | None,
            group_avg_price: Decimal | None,
            ratio: Decimal | None,
    ) -> str | None:
        if not (is_explicit_hit or is_stat_hit):
            return None

        if is_explicit_hit and is_stat_hit:
            return (
                f"疑似异常低价：同时命中显式阈值与统计规则，"
                f"当前价格={current_price}，显式阈值={explicit_threshold}，"
                f"组均价={group_avg_price}，当前/均价={ratio}"
            )

        if is_explicit_hit:
            return (
                f"疑似异常低价：命中显式阈值规则，"
                f"当前价格={current_price}，显式阈值={explicit_threshold}"
            )

        return (
            f"疑似异常低价：命中统计低价规则，"
            f"当前价格={current_price}，组均价={group_avg_price}，当前/均价={ratio}"
        )

    def _build_spec_risk_reason(
            self,
            title_mismatch: bool,
            missing_normalized_spec: bool,
            clean_spec: str,
            title_spec_hint: str,
    ) -> str | None:
        if not (title_mismatch or missing_normalized_spec):
            return None

        reasons: list[str] = []
        if title_mismatch:
            reasons.append(
                f"规格识别风险：规格列={clean_spec or '-'}，标题规格={title_spec_hint or '-'}"
            )
        if missing_normalized_spec:
            reasons.append("规格识别风险：归一规格缺失")

        return "；".join(reasons)

    # ==========
    # 小工具
    # ==========

    def _pick_primary_low_price_rule(
            self,
            explicit_rule: RuleDefinition | None,
            stat_rule: RuleDefinition | None,
            is_explicit_hit: bool,
            is_stat_hit: bool,
    ) -> RuleDefinition | None:
        if is_explicit_hit:
            return explicit_rule
        if is_stat_hit:
            return stat_rule
        return None

    def _get_low_price_rule_source(
            self,
            is_explicit_hit: bool,
            is_stat_hit: bool,
    ) -> str | None:
        if is_explicit_hit and is_stat_hit:
            return "both"
        if is_explicit_hit:
            return "explicit_rule"
        if is_stat_hit:
            return "stat_rule"
        return None

    def _find_first_existing_column(
            self,
            df: pd.DataFrame,
            candidates: list[str],
    ) -> str | None:
        normalized_map = {
            str(col).replace("\ufeff", "").strip(): col
            for col in df.columns
        }
        for candidate in candidates:
            key = str(candidate).replace("\ufeff", "").strip()
            if key in normalized_map:
                return normalized_map[key]
        return None

    def _safe_to_bool(self, value: object) -> bool:
        if pd.isna(value):
            return False
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        return text in {"true", "1", "yes", "y"}

    def _to_str(self, value: object) -> str:
        if value is None or pd.isna(value):
            return ""
        return str(value).strip()

    def _to_decimal(self, value: object) -> Decimal | None:
        if value is None or pd.isna(value):
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _json_number(self, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    def _json_obj(self, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return value if isinstance(value, dict) else None
