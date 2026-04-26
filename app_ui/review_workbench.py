# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.getenv("PRICE_AUDIT_API_BASE_URL", "http://127.0.0.1:8000")

STATUS_LABELS = {
    "pending": "待复核",
    "processing": "处理中",
    "confirmed": "已确认异常",
    "rejected": "已判定误报",
    "ignored": "已忽略",
    "closed": "已关闭",
    "done": "已完成",
}

ACTION_LABELS = {
    "add_remark": "添加备注",
    "confirm_abnormal": "确认异常",
    "mark_false_positive": "标记误报",
    "ignore_task": "忽略任务",
    "close_task": "关闭任务",
}

PRIORITY_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
}


def api_request(
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    url = f"{API_BASE_URL}{path}"

    try:
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=json_body,
            timeout=30,
        )
    except requests.RequestException as exc:
        st.error(f"请求后端失败：{exc}")
        return None

    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text}

    if response.status_code >= 400:
        st.error(f"接口请求失败：{response.status_code}")
        st.code(data)
        return None

    return data


def format_status(status: str | None) -> str:
    if not status:
        return "-"
    return STATUS_LABELS.get(status, status)


def format_priority(priority: str | None) -> str:
    if not priority:
        return "-"
    return PRIORITY_LABELS.get(priority, priority)


def get_allowed_actions(task_status: str | None) -> dict[str, bool]:
    """
    返回当前状态下允许执行哪些状态动作。
    add_comment 不在这里控制，备注始终允许。
    """

    if task_status in {"pending", "processing"}:
        return {
            "confirm": True,
            "reject": True,
            "ignore": True,
            "close": False,
        }

    if task_status in {"confirmed", "rejected", "ignored"}:
        return {
            "confirm": False,
            "reject": False,
            "ignore": False,
            "close": True,
        }

    return {
        "confirm": False,
        "reject": False,
        "ignore": False,
        "close": False,
    }


def get_status_action_tip(task_status: str | None) -> str:
    if task_status in {"pending", "processing"}:
        return "当前任务可执行：确认异常、标记误报、忽略任务。"

    if task_status in {"confirmed", "rejected", "ignored"}:
        return "当前任务已有复核结论，只允许关闭任务或继续添加备注。"

    if task_status == "closed":
        return "当前任务已关闭，不允许再执行状态动作，只能查看记录或添加备注。"

    return "当前状态不支持状态动作。"


def normalize_task_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for item in items:
        rows.append(
            {
                "任务ID": item.get("id"),
                "审核结果ID": item.get("audit_result_id"),
                "状态": format_status(item.get("task_status")),
                "优先级": format_priority(item.get("priority")),
                "分配给": item.get("assigned_to") or "-",
                "创建人": item.get("created_by") or "-",
                "截止时间": item.get("due_at") or "-",
                "创建时间": item.get("created_at") or "-",
            }
        )

    return rows


def render_sidebar_filters() -> dict[str, Any]:
    st.sidebar.header("筛选条件")

    status_options = {
        "全部": None,
        "待复核": "pending",
        "处理中": "processing",
        "已确认异常": "confirmed",
        "已判定误报": "rejected",
        "已忽略": "ignored",
        "已关闭": "closed",
    }

    priority_options = {
        "全部": None,
        "低": "low",
        "中": "medium",
        "高": "high",
    }

    status_label = st.sidebar.selectbox(
        "任务状态",
        list(status_options.keys()),
        index=0,
    )

    priority_label = st.sidebar.selectbox(
        "优先级",
        list(priority_options.keys()),
        index=0,
    )

    assigned_to = st.sidebar.text_input(
        "分配对象",
        value="",
        placeholder="例如：董宏升",
    ).strip()

    page_size = st.sidebar.slider(
        "每页数量",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
    )

    return {
        "task_status": status_options[status_label],
        "priority": priority_options[priority_label],
        "assigned_to": assigned_to or None,
        "page": 1,
        "page_size": page_size,
    }


def fetch_tasks(filters: dict[str, Any]) -> dict[str, Any] | None:
    params = {
        key: value
        for key, value in filters.items()
        if value is not None and value != ""
    }

    return api_request(
        "GET",
        "/api/v1/reviews/tasks",
        params=params,
    )


def fetch_task_detail(task_id: int) -> dict[str, Any] | None:
    return api_request(
        "GET",
        f"/api/v1/reviews/tasks/{task_id}",
    )


def fetch_export() -> dict[str, Any] | None:
    return api_request(
        "GET",
        "/api/v1/reviews/export",
    )


def post_comment(task_id: int, reviewer: str, remark: str) -> bool:
    data = api_request(
        "POST",
        f"/api/v1/reviews/tasks/{task_id}/comment",
        json_body={
            "reviewer": reviewer,
            "remark": remark,
        },
    )
    return data is not None


def post_action(
        task_id: int,
        action: str,
        reviewer: str,
        remark: str,
) -> bool:
    path_map = {
        "confirm": f"/api/v1/reviews/tasks/{task_id}/confirm",
        "reject": f"/api/v1/reviews/tasks/{task_id}/reject",
        "ignore": f"/api/v1/reviews/tasks/{task_id}/ignore",
        "close": f"/api/v1/reviews/tasks/{task_id}/close",
    }

    path = path_map[action]

    data = api_request(
        "POST",
        path,
        json_body={
            "reviewer": reviewer,
            "remark": remark,
        },
    )

    return data is not None


def call_explanation(audit_result_id: int) -> dict[str, Any] | None:
    """
    调用 6号窗口已经交接的 /ask explanation 主链。

    这里不是重新解释异常，而是复用 /ask 对 audit_result_id 的解释能力。
    """

    payload = {
        "question": f"请解释 audit_result_id={audit_result_id} 为什么被判异常，并给出规则依据。",
        "audit_result_id": audit_result_id,
        "include_trace": True,
    }

    return api_request(
        "POST",
        "/ask",
        json_body=payload,
    )


def render_audit_snapshot(audit_snapshot: dict[str, Any]) -> None:
    st.subheader("审核结果快照")

    if not audit_snapshot:
        st.info("暂无审核快照")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("审核结果ID", audit_snapshot.get("audit_result_id", "-"))
        st.write("**清洗数据ID：**", audit_snapshot.get("clean_id", "-"))
        st.write("**异常类型：**", audit_snapshot.get("anomaly_type", "-"))

    with col2:
        st.write("**是否命中：**", audit_snapshot.get("is_hit", "-"))
        st.write("**命中规则：**", audit_snapshot.get("hit_rule_code", "-"))
        st.write("**规则版本：**", audit_snapshot.get("hit_rule_version", "-"))

    with col3:
        st.write("**结果状态：**", audit_snapshot.get("result_status", "-"))
        st.write("**低价规则来源：**", audit_snapshot.get("low_price_rule_source", "-"))
        st.write("**判定时间：**", audit_snapshot.get("audited_at", "-"))

    st.write("**异常原因：**")
    st.info(audit_snapshot.get("reason_text") or "暂无异常原因")

    with st.expander("查看输入快照 input_snapshot_json"):
        st.json(audit_snapshot.get("input_snapshot_json") or {})


def render_records(records: list[dict[str, Any]]) -> None:
    st.subheader("复核记录")

    if not records:
        st.info("暂无复核记录")
        return

    for record in records:
        action_type = record.get("action_type")
        action_label = ACTION_LABELS.get(action_type, action_type)

        with st.expander(
                f"{action_label}｜{record.get('reviewer') or '-'}｜{record.get('created_at')}",
                expanded=False,
        ):
            st.write("**动作类型：**", action_type)
            st.write("**动作结果：**", record.get("action_result") or "-")
            st.write("**复核人：**", record.get("reviewer") or "-")
            st.write("**备注：**", record.get("remark") or "-")

            snapshot = record.get("evidence_snapshot_json")
            if snapshot:
                st.write("**依据快照：**")
                st.json(snapshot)


def unwrap_api_payload(data: dict[str, Any] | None) -> dict[str, Any]:
    """
    兼容两类返回：
    1. 直接返回业务结构
    2. 统一响应外壳：{"success": true, "data": {...}}
    """
    if not data:
        return {}

    if isinstance(data, dict) and "data" in data and isinstance(data.get("data"), dict):
        return data["data"]

    return data


def safe_text(value: Any, default: str = "-") -> str:
    if value is None:
        return default

    if value == "":
        return default

    return str(value)


def render_kv_grid(title: str, kv: dict[str, Any], columns: int = 3) -> None:
    st.markdown(f"#### {title}")

    items = list(kv.items())

    if not items:
        st.info("暂无数据")
        return

    cols = st.columns(columns)

    for index, (key, value) in enumerate(items):
        with cols[index % columns]:
            st.caption(key)
            st.write(safe_text(value))


def render_rule_facts_card(rule_facts: dict[str, Any]) -> None:
    st.markdown("#### 结果层事实")

    if not rule_facts:
        st.info("暂无 rule_facts")
        return

    core_facts = {
        "审核结果ID": rule_facts.get("audit_result_id"),
        "清洗数据ID": rule_facts.get("clean_id"),
        "异常类型": rule_facts.get("anomaly_type"),
        "是否命中": rule_facts.get("is_hit"),
        "命中规则": rule_facts.get("hit_rule_code"),
        "规则版本": rule_facts.get("hit_rule_version"),
    }

    render_kv_grid("核心事实", core_facts, columns=3)

    reason_text = rule_facts.get("reason_text")
    if reason_text:
        st.markdown("**判定原因：**")
        st.info(reason_text)

    hit_messages = rule_facts.get("hit_messages")
    if hit_messages:
        st.markdown("**规则命中信息：**")
        if isinstance(hit_messages, list):
            for msg in hit_messages:
                st.write(f"- {msg}")
        else:
            st.write(hit_messages)

    with st.expander("查看 input_snapshot / threshold_snapshot / computed_value", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**input_snapshot**")
            st.json(rule_facts.get("input_snapshot") or {})

        with col2:
            st.markdown("**threshold_snapshot**")
            st.json(rule_facts.get("threshold_snapshot") or {})

        with col3:
            st.markdown("**computed_value**")
            st.json(rule_facts.get("computed_value") or {})


def get_evidence_title(evidence: dict[str, Any], index: int) -> str:
    doc_title = (
            evidence.get("doc_title")
            or evidence.get("document_title")
            or evidence.get("source_title")
            or evidence.get("title")
            or "未知证据"
    )

    section_title = (
            evidence.get("section_title")
            or evidence.get("section")
            or evidence.get("heading")
            or ""
    )

    if section_title:
        return f"证据 {index}｜{doc_title}｜{section_title}"

    return f"证据 {index}｜{doc_title}"


def render_evidence_cards(evidences: list[dict[str, Any]]) -> None:
    st.markdown("#### 规则证据")

    if not evidences:
        st.info("暂无 evidences")
        return

    for index, evidence in enumerate(evidences, start=1):
        title = get_evidence_title(evidence, index)

        score = evidence.get("score")
        evidence_type = evidence.get("evidence_type") or evidence.get("source_type") or "-"
        chunk_id = evidence.get("chunk_id") or "-"
        rule_code = evidence.get("rule_code") or evidence.get("hit_rule_code") or "-"
        rule_version = evidence.get("rule_version") or evidence.get("hit_rule_version") or "-"

        with st.container(border=True):
            st.markdown(f"**{title}**")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.caption("证据类型")
                st.write(safe_text(evidence_type))

            with col2:
                st.caption("chunk_id")
                st.write(safe_text(chunk_id))

            with col3:
                st.caption("规则")
                st.write(safe_text(rule_code))

            with col4:
                st.caption("版本 / 分数")
                if score is not None:
                    st.write(f"{safe_text(rule_version)} / {score}")
                else:
                    st.write(safe_text(rule_version))

            preview = (
                    evidence.get("preview_text")
                    or evidence.get("quoted_preview")
                    or evidence.get("body_text")
                    or evidence.get("full_text")
                    or evidence.get("content")
            )

            if preview:
                st.markdown("**依据内容：**")
                st.info(preview)

            score_reasons = evidence.get("score_reasons")
            if score_reasons:
                with st.expander("查看命中原因", expanded=False):
                    if isinstance(score_reasons, list):
                        for reason in score_reasons:
                            st.write(f"- {reason}")
                    else:
                        st.write(score_reasons)

            with st.expander("查看原始 evidence", expanded=False):
                st.json(evidence)


def get_citation_title(citation: dict[str, Any], index: int) -> str:
    doc_title = (
            citation.get("doc_title")
            or citation.get("document_title")
            or citation.get("source_title")
            or citation.get("title")
            or "未知引用"
    )

    section_title = citation.get("section_title") or citation.get("section") or ""

    if section_title:
        return f"引用 {index}｜{doc_title}｜{section_title}"

    return f"引用 {index}｜{doc_title}"


def render_citation_cards(citations: list[dict[str, Any]]) -> None:
    st.markdown("#### 引用来源")

    if not citations:
        st.info("暂无 citations")
        return

    for index, citation in enumerate(citations, start=1):
        title = get_citation_title(citation, index)

        chunk_id = citation.get("chunk_id") or "-"
        citation_note = citation.get("citation_note") or citation.get("note") or ""
        quoted_preview = citation.get("quoted_preview") or citation.get("preview_text") or ""

        with st.container(border=True):
            st.markdown(f"**{title}**")

            col1, col2 = st.columns([0.25, 0.75])

            with col1:
                st.caption("chunk_id")
                st.write(safe_text(chunk_id))

            with col2:
                st.caption("引用说明")
                st.write(safe_text(citation_note))

            if quoted_preview:
                st.markdown("**引用片段：**")
                st.info(quoted_preview)

            with st.expander("查看原始 citation", expanded=False):
                st.json(citation)


def render_trace_card(trace: Any) -> None:
    if not trace:
        return

    with st.expander("trace 调用链", expanded=False):
        st.json(trace)


def render_raw_explanation_json(explanation_result: dict[str, Any]) -> None:
    with st.expander("查看原始 explanation_result JSON", expanded=False):
        st.json(explanation_result)


def render_explanation_panel(audit_result_id: int) -> None:
    st.subheader("规则解释与依据")

    state_key = f"latest_explanation_{audit_result_id}"

    col1, col2 = st.columns([0.75, 0.25])

    with col1:
        st.caption("复用 6号窗口 /ask explanation 主链，不在工作台里重新判定异常。")

    with col2:
        if st.button(
                "获取规则依据",
                width="stretch",
                key=f"fetch_explanation_{audit_result_id}",
        ):
            data = call_explanation(audit_result_id)

            if not data:
                return

            st.session_state[state_key] = unwrap_api_payload(data)

    explanation = st.session_state.get(state_key)

    if not explanation:
        st.info("点击“获取规则依据”后，将展示解释摘要、结果层事实、规则证据和引用来源。")
        return

    answer = explanation.get("answer")
    explanation_result = explanation.get("explanation_result") or {}

    final_summary = (
            explanation_result.get("final_summary")
            or explanation_result.get("summary")
            or answer
            or "暂无解释摘要"
    )

    st.markdown("#### 解释摘要")
    st.success(final_summary)

    route = explanation.get("route")
    route_reason = explanation.get("route_reason")
    retrieval_mode = explanation.get("retrieval_mode")

    meta_cols = st.columns(3)

    with meta_cols[0]:
        st.caption("路由")
        st.write(safe_text(route))

    with meta_cols[1]:
        st.caption("检索模式")
        st.write(safe_text(retrieval_mode))

    with meta_cols[2]:
        st.caption("路由原因")
        st.write(safe_text(route_reason))

    rule_facts = explanation_result.get("rule_facts") or {}
    evidences = explanation_result.get("evidences") or []
    citations = explanation_result.get("citations") or []

    st.divider()

    render_rule_facts_card(rule_facts)

    st.divider()

    left, right = st.columns([1, 1])

    with left:
        render_evidence_cards(evidences)

    with right:
        render_citation_cards(citations)

    render_trace_card(explanation.get("trace"))

    render_raw_explanation_json(explanation_result)


def render_action_panel(task_id: int, task_status: str | None) -> None:
    st.subheader("复核操作")

    st.info(get_status_action_tip(task_status))

    allowed_actions = get_allowed_actions(task_status)

    reviewer = st.text_input(
        "复核人",
        value="董宏升",
        key=f"reviewer_{task_id}",
    )

    remark = st.text_area(
        "复核备注",
        value="",
        placeholder="请输入本次复核意见，例如：已核对规则依据，确认该商品存在规格识别风险。",
        key=f"remark_{task_id}",
        height=120,
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button(
                "确认异常",
                type="primary",
                width="stretch",
                disabled=not allowed_actions["confirm"],
        ):
            if post_action(task_id, "confirm", reviewer, remark):
                st.success("已确认异常")
                st.rerun()

    with col2:
        if st.button(
                "标记误报",
                width="stretch",
                disabled=not allowed_actions["reject"],
        ):
            if post_action(task_id, "reject", reviewer, remark):
                st.success("已标记为误报")
                st.rerun()

    with col3:
        if st.button(
                "忽略任务",
                width="stretch",
                disabled=not allowed_actions["ignore"],
        ):
            if post_action(task_id, "ignore", reviewer, remark):
                st.success("已忽略任务")
                st.rerun()

    with col4:
        if st.button(
                "关闭任务",
                width="stretch",
                disabled=not allowed_actions["close"],
        ):
            if post_action(task_id, "close", reviewer, remark):
                st.success("已关闭任务")
                st.rerun()

    with st.form(f"comment_form_{task_id}"):
        comment = st.text_area(
            "仅添加备注，不改变任务状态",
            placeholder="例如：已电话同步业务同事，等待进一步确认。",
            height=100,
        )

        submitted = st.form_submit_button("添加备注")

        if submitted:
            if not comment.strip():
                st.warning("备注不能为空")
            elif post_comment(task_id, reviewer, comment.strip()):
                st.success("备注已添加")
                st.rerun()


def render_export_panel() -> None:
    st.subheader("导出复核结果")

    data = fetch_export()

    if not data:
        st.info("暂无导出数据")
        return

    items = data.get("items", [])

    if not items:
        st.info("暂无复核结果")
        return

    st.dataframe(items, use_container_width=True)

    st.download_button(
        label="下载 JSON 导出结果",
        data=str(items),
        file_name="review_export.json",
        mime="application/json",
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="人工复核工作台",
        page_icon="✅",
        layout="wide",
    )

    st.title("人工复核工作台")
    st.caption("7号窗口：把异常结果、规则依据、人工判断、复核留痕串成业务闭环")

    st.sidebar.write("后端地址：")
    st.sidebar.code(API_BASE_URL)

    filters = render_sidebar_filters()

    task_data = fetch_tasks(filters)

    if task_data is None:
        st.stop()

    items = task_data.get("items", [])
    total = task_data.get("total", 0)

    st.subheader("异常复核任务列表")
    st.write(f"当前共查询到 **{total}** 条复核任务")

    if not items:
        st.info("暂无复核任务")
        render_export_panel()
        return

    rows = normalize_task_items(items)
    st.dataframe(rows, use_container_width=True, hide_index=True)

    task_id_options = [item["id"] for item in items]

    selected_task_id = st.selectbox(
        "选择要处理的复核任务",
        task_id_options,
        format_func=lambda task_id: f"任务 #{task_id}",
    )

    detail = fetch_task_detail(int(selected_task_id))

    if not detail:
        st.stop()

    task = detail.get("task", {})
    records = detail.get("records", [])
    audit_snapshot = detail.get("audit_snapshot", {})

    st.divider()

    left, right = st.columns([1.15, 0.85])

    with left:
        st.subheader("复核任务详情")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("任务ID", task.get("id", "-"))
            st.write("**状态：**", format_status(task.get("task_status")))

        with col2:
            st.metric("审核结果ID", task.get("audit_result_id", "-"))
            st.write("**优先级：**", format_priority(task.get("priority")))

        with col3:
            st.write("**分配给：**", task.get("assigned_to") or "-")
            st.write("**创建人：**", task.get("created_by") or "-")
            st.write("**创建时间：**", task.get("created_at") or "-")

        render_audit_snapshot(audit_snapshot)

        audit_result_id = audit_snapshot.get("audit_result_id") or task.get("audit_result_id")
        if audit_result_id:
            render_explanation_panel(int(audit_result_id))

    with right:
        render_action_panel(
            int(selected_task_id),
            task.get("task_status"),
        )
        render_records(records)

    st.divider()
    render_export_panel()


if __name__ == "__main__":
    main()
