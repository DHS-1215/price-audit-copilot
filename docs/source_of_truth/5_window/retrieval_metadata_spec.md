# Retrieval Metadata 规范

## 1. 文档目的

本文档用于定义 5号窗口中规则检索相关 metadata 的正式口径，包括 metadata 的字段结构、使用范围、在 baseline
检索中的作用、在向量检索中的作用、在混合检索中的作用、在 rerank 预留中的作用，以及 metadata 如何支撑 evidence / citation 输出。

本文件是 5号窗口：规则解释 / RAG 检索解释窗口 的 source of truth 文档之一。

本文档要解决的问题包括：

- 检索时 metadata 至少应该包含哪些字段；
- baseline retriever 如何使用 metadata；
- vector retriever 如何使用 metadata；
- hybrid retriever 如何融合 metadata；
- rerank 预留时需要保留哪些分数字段；
- explanation 场景如何防止证据漂移；
- retrieval 场景如何保证结果可追溯；
- 检索结果为什么命中，如何通过 score_reasons 说明。

一句话：

> metadata 是规则检索系统的结构化锚点，用来保证 RAG 结果不是“搜到哪算哪”，而是能追到规则、版本、文档、章节和命中原因。

---

## 2. metadata 的定位

metadata 是附加在 `rule_chunk` 上的结构化检索信息。

它不是规则正文，但它决定了检索系统能不能精准定位规则依据。

metadata 的作用包括：

1. 约束 explanation 场景的检索范围；
2. 支撑 baseline retriever 的规则打分；
3. 增强 vector retriever 的召回稳定性；
4. 支撑 hybrid retriever 的结果融合；
5. 支撑 rerank 的候选重排；
6. 支撑 evidence 的结构化输出；
7. 支撑 citation 的来源展示；
8. 支撑后续 `/ask` 编排层复用检索结果。

没有 metadata，RAG 很容易退化为普通文本搜索。

在本项目中，metadata 必须服务于维价审核业务，而不是只服务于语义相似度。

---

## 3. metadata 与核心对象的关系

metadata 依附于 `rule_chunk`，但它必须能连接到以下对象：

    audit_result
    rule_hit
    rule_definition
    rule_chunk

在 explanation 场景中，metadata 的主要作用是把 `rule_chunk` 约束到当前异常事实对应的规则范围内。

解释链路固定为：

    audit_result -> rule_hit -> rule_definition -> rule_chunk

metadata 主要服务最后一步：

    根据 rule_hit / rule_definition 找到相关 rule_chunk

它不能反过来替代前面的结果层事实。

---

## 4. metadata 最小字段集合

`rule_chunk.metadata_json` 至少应包含以下字段。

| 字段名                     | 类型建议           | 是否必需 | 说明       |
|-------------------------|----------------|-----:|----------|
| `rule_code`             | string         |    是 | 规则编码     |
| `rule_name`             | string         |   建议 | 规则名称     |
| `rule_type`             | string         |   建议 | 规则类型     |
| `rule_version`          | string         |    是 | 规则版本     |
| `anomaly_type`          | string         |    是 | 异常类型     |
| `source_doc_path`       | string         |    是 | 来源文档路径   |
| `doc_title`             | string         |    是 | 文档标题     |
| `section_title`         | string         |    是 | 当前章节标题   |
| `section_path`          | string         |    是 | 完整章节路径   |
| `chunk_type`            | string         |    是 | chunk 类型 |
| `keywords`              | array          |   建议 | 关键词      |
| `tags`                  | array          |   建议 | 标签       |
| `is_active`             | bool           |    是 | 是否启用     |
| `priority`              | int / nullable |   可选 | 检索优先级    |
| `related_rule_codes`    | array          |   可选 | 相关规则编码   |
| `related_anomaly_types` | array          |   可选 | 相关异常类型   |

---

## 5. 字段说明

### 5.1 rule_code

`rule_code` 是规则编码。

当前已确认的核心规则编码包括：

    LOW_PRICE_EXPLICIT
    LOW_PRICE_STAT
    CROSS_PLATFORM_GAP
    SPEC_RISK

在 explanation 场景中，`rule_code` 是最重要的强约束字段之一。

如果 `rule_hit.rule_code = LOW_PRICE_EXPLICIT`，那么优先检索 `metadata.rule_code = LOW_PRICE_EXPLICIT` 的 chunk。

---

### 5.2 rule_name

`rule_name` 是规则名称。

示例：

    显式低价规则
    统计低价规则
    跨平台价差规则
    规格识别风险规则

`rule_name` 主要用于展示和辅助检索，不应作为唯一匹配依据。

---

### 5.3 rule_type

`rule_type` 是规则类型。

建议取值可包括：

    low_price
    cross_platform_gap
    spec_risk
    manual_review
    faq

如果当前项目中 `rule_definition.rule_type` 已有正式口径，应优先与其保持一致。

---

### 5.4 rule_version

`rule_version` 是规则版本。

它用于保证解释依据尽量和判定时使用的规则版本一致。

在 explanation 场景中，优先级为：

    rule_code 精确匹配 + rule_version 精确匹配
        高于
    rule_code 精确匹配 + 当前启用版本

如果找不到完全匹配版本，应在 evidence 或 trace_notes 中记录：

    未找到完全匹配规则版本，使用当前启用文档依据。

---

### 5.5 anomaly_type

`anomaly_type` 是异常类型。

当前正式取值为：

    low_price
    cross_platform_gap
    spec_risk

不要使用以下非正式简称：

    gap
    price_gap
    spec
    low

`anomaly_type` 用于：

1. 约束 explanation 场景；
2. 辅助 retrieval 场景；
3. 支撑后续 `/ask` 路由；
4. 支撑 evidence / citation 展示。

---

### 5.6 source_doc_path

`source_doc_path` 是规则文档路径。

示例：

    docs/rules/low_price_rules.md
    docs/rules/cross_platform_gap_rules.md
    docs/rules/spec_risk_rules.md
    docs/rules/manual_review_rules.md
    docs/rules/rule_faq.md

用途：

1. 支撑 citation 展示；
2. 支撑文档追溯；
3. 支撑 chunk 重建；
4. 支撑人工排查；
5. 支撑 score_reasons 输出。

---

### 5.7 doc_title

`doc_title` 是文档标题。

示例：

    低价异常规则说明
    跨平台价差规则说明
    规格识别风险规则说明
    人工复核流程说明
    规则 FAQ

`doc_title` 可以参与 baseline 检索加权。

---

### 5.8 section_title

`section_title` 是当前 chunk 所属章节标题。

示例：

    显式低价规则
    统计低价规则
    价差比例阈值
    标题规格冲突
    规范化规格缺失

它是 citation 展示的重要字段。

---

### 5.9 section_path

`section_path` 是完整章节路径。

示例：

    低价异常规则说明 > 显式低价规则 > 阈值口径
    规格识别风险规则说明 > 标题规格冲突
    人工复核流程说明 > 复核动作 > 标记误报

`section_path` 比 `section_title` 更适合做引用定位。

---

### 5.10 chunk_type

`chunk_type` 表示 chunk 类型。

推荐取值：

| chunk_type      | 说明     |
|-----------------|--------|
| `rule_text`     | 正式规则说明 |
| `definition`    | 概念定义   |
| `threshold`     | 阈值说明   |
| `example`       | 示例说明   |
| `manual_review` | 人工复核流程 |
| `faq`           | 常见问题   |
| `note`          | 注意事项   |

在 explanation 场景中，优先级建议为：

    threshold / rule_text > definition > example > manual_review > faq > note

FAQ 和人工复核类 chunk 可以作为补充说明，但不应替代正式规则说明。

---

### 5.11 keywords

`keywords` 是关键词列表。

示例：

    ["低价", "显式阈值", "500ml", "498", "LOW_PRICE_EXPLICIT"]

用途：

1. 支撑 baseline 检索；
2. 支撑 score_reasons；
3. 支撑人工排查；
4. 支撑向量检索文本拼接。

---

### 5.12 tags

`tags` 是标签列表。

示例：

    ["价格异常", "显式规则", "阈值", "人工复核"]

`tags` 比 keywords 更偏分类，keywords 更偏检索命中。

---

### 5.13 is_active

`is_active` 表示当前 chunk 是否启用。

默认检索只应检索：

    is_active = true

旧版、废弃、归档 chunk 可以保留，但不应进入默认主链检索。

---

### 5.14 priority

`priority` 是可选检索优先级字段。

如果多个 chunk 都命中同一规则，可以通过 `priority` 控制优先级。

建议：

    100 = 核心规则说明
    80 = 阈值说明
    60 = 示例说明
    40 = FAQ
    20 = 注意事项

当前阶段不强制实现，但可以预留。

---

### 5.15 related_rule_codes

`related_rule_codes` 用于记录一个 chunk 可能关联的多个规则编码。

示例：

    ["LOW_PRICE_EXPLICIT", "LOW_PRICE_STAT"]

适用于：

1. 综合说明类 chunk；
2. FAQ 类 chunk；
3. 人工复核类 chunk。

主归属规则仍应优先写入 `rule_code`。

---

### 5.16 related_anomaly_types

`related_anomaly_types` 用于记录一个 chunk 可能关联的多个异常类型。

示例：

    ["low_price", "spec_risk"]

适用于：

1. FAQ；
2. 人工复核流程；
3. 综合说明文档。

---

## 6. metadata 示例

### 6.1 低价规则 chunk metadata 示例

    {
      "rule_code": "LOW_PRICE_EXPLICIT",
      "rule_name": "显式低价规则",
      "rule_type": "low_price",
      "rule_version": "v1",
      "anomaly_type": "low_price",
      "source_doc_path": "docs/rules/low_price_rules.md",
      "doc_title": "低价异常规则说明",
      "section_title": "显式低价规则",
      "section_path": "低价异常规则说明 > 显式低价规则 > 阈值口径",
      "chunk_type": "threshold",
      "keywords": ["低价", "显式阈值", "500ml", "498", "LOW_PRICE_EXPLICIT"],
      "tags": ["价格异常", "阈值", "显式规则"],
      "is_active": true,
      "priority": 100
    }

---

### 6.2 跨平台价差 chunk metadata 示例

    {
      "rule_code": "CROSS_PLATFORM_GAP",
      "rule_name": "跨平台价差规则",
      "rule_type": "cross_platform_gap",
      "rule_version": "v1",
      "anomaly_type": "cross_platform_gap",
      "source_doc_path": "docs/rules/cross_platform_gap_rules.md",
      "doc_title": "跨平台价差规则说明",
      "section_title": "价差比例阈值",
      "section_path": "跨平台价差规则说明 > 判定口径 > 价差比例阈值",
      "chunk_type": "rule_text",
      "keywords": ["跨平台", "价差", "最低价", "价差比例"],
      "tags": ["价格异常", "平台对比", "价差"],
      "is_active": true,
      "priority": 100
    }

---

### 6.3 规格风险 chunk metadata 示例

    {
      "rule_code": "SPEC_RISK",
      "rule_name": "规格识别风险规则",
      "rule_type": "spec_risk",
      "rule_version": "v1",
      "anomaly_type": "spec_risk",
      "source_doc_path": "docs/rules/spec_risk_rules.md",
      "doc_title": "规格识别风险规则说明",
      "section_title": "标题规格冲突",
      "section_path": "规格识别风险规则说明 > 标题规格冲突",
      "chunk_type": "rule_text",
      "keywords": ["规格", "标题规格", "规格列", "冲突", "SPEC_RISK"],
      "tags": ["规格风险", "人工复核"],
      "is_active": true,
      "priority": 100
    }

---

### 6.4 人工复核 chunk metadata 示例

    {
      "rule_code": null,
      "rule_name": "人工复核流程",
      "rule_type": "manual_review",
      "rule_version": "v1",
      "anomaly_type": null,
      "source_doc_path": "docs/rules/manual_review_rules.md",
      "doc_title": "人工复核流程说明",
      "section_title": "标记误报",
      "section_path": "人工复核流程说明 > 复核动作 > 标记误报",
      "chunk_type": "manual_review",
      "keywords": ["人工复核", "误报", "确认异常", "备注"],
      "tags": ["复核", "状态流转"],
      "is_active": true,
      "priority": 60,
      "related_anomaly_types": ["low_price", "cross_platform_gap", "spec_risk"]
    }

---

## 7. baseline 检索使用方式

baseline retriever 应优先使用 metadata 做结构化匹配。

baseline 不是简单全文搜索，而是基于规则字段、章节字段、关键词字段进行加权检索。

### 7.1 explanation 场景

explanation 场景输入通常来自：

    audit_result
    rule_hit
    rule_definition

优先匹配字段：

1. `rule_code`
2. `rule_version`
3. `anomaly_type`
4. `source_doc_path`
5. `chunk_type`
6. `section_title`
7. `keywords`
8. `chunk_text`

推荐优先级：

    rule_code 精确匹配
        >
    rule_version 匹配
        >
    anomaly_type 匹配
        >
    chunk_type 为 rule_text / threshold
        >
    section_title / keywords 命中
        >
    chunk_text 正文命中

---

### 7.2 retrieval 场景

retrieval 场景输入通常来自用户 query，例如：

    低价异常是怎么判断的？
    跨平台价差规则是什么？
    规格风险为什么要人工复核？

可匹配字段：

1. `doc_title`
2. `section_title`
3. `section_path`
4. `keywords`
5. `tags`
6. `rule_code`
7. `anomaly_type`
8. `chunk_text`

retrieval 场景允许更依赖自然语言 query，但仍必须返回可追溯的 metadata。

---

## 8. baseline score_reasons 规范

baseline retriever 返回结果时，应尽量输出 `score_reasons`。

推荐原因枚举：

| score_reason            | 说明            |
|-------------------------|---------------|
| `rule_code_exact_match` | 规则编码精确匹配      |
| `rule_version_match`    | 规则版本匹配        |
| `anomaly_type_match`    | 异常类型匹配        |
| `source_doc_path_match` | 来源文档路径匹配      |
| `doc_title_match`       | 文档标题匹配        |
| `section_title_match`   | 章节标题匹配        |
| `keyword_match`         | 关键词匹配         |
| `tag_match`             | 标签匹配          |
| `chunk_text_match`      | 正文命中          |
| `chunk_type_priority`   | chunk 类型优先级加权 |
| `is_active_filter`      | 仅命中启用 chunk   |

示例：

    {
      "chunk_id": 12,
      "score": 18.5,
      "score_reasons": [
        "rule_code_exact_match",
        "anomaly_type_match",
        "section_title_match",
        "keyword_match"
      ]
    }

---

## 9. 向量检索使用方式

向量检索用于补充 baseline 的自然语言召回短板。

它主要解决：

1. 用户问题和规则文档表达不完全一致；
2. 用户使用同义说法；
3. 用户问题比较长；
4. 用户询问 FAQ 或流程时没有明确规则编码；
5. baseline 无法命中关键词但语义相关。

---

## 10. 向量化文本构造规范

向量化时不建议只使用 `chunk_text`。

推荐组合以下字段：

    doc_title
    section_title
    section_path
    rule_code
    anomaly_type
    chunk_text

示例拼接格式：

    文档：低价异常规则说明
    章节：显式低价规则 > 阈值口径
    规则编码：LOW_PRICE_EXPLICIT
    异常类型：low_price
    内容：……

这样做的好处：

1. chunk 本身上下文更完整；
2. 向量召回不容易丢规则归属；
3. 检索结果更容易解释；
4. 后续 evidence / citation 更稳定。

---

## 11. 向量检索结果必须保留 metadata

vector retriever 返回结果时，不允许只返回文本和分数。

必须返回：

1. `chunk_id`
2. `chunk_text`
3. `score`
4. `metadata`
5. `doc_title`
6. `section_title`
7. `section_path`
8. `rule_code`
9. `rule_version`
10. `anomaly_type`
11. `source_doc_path`

否则后续无法构建 evidence 和 citation。

---

## 12. explanation 场景下的向量检索约束

explanation 场景中，向量检索不能自由发散。

必须遵守：

1. 优先受 `audit_result.anomaly_type` 约束；
2. 优先受 `rule_hit.rule_code` 约束；
3. 优先受 `rule_definition.version` 约束；
4. 不允许只靠语义相似度选取最终依据；
5. 如果 vector 结果与 baseline 强匹配结果冲突，应优先采用 baseline 强匹配结果；
6. 如果 vector 召回了不同异常类型的文档，必须降权或过滤。

错误示例：

    audit_result 显示 low_price
    vector 检索却主要返回 spec_risk 文档
    解释服务直接引用 spec_risk 文档说明低价异常

这种情况不允许进入正式解释输出。

---

## 13. retrieval 场景下的向量检索约束

retrieval 场景允许向量检索发挥更大作用。

适合使用向量检索的问题包括：

    为什么有时候规格识别风险需要人工复核？
    价格差很多为什么只标最低价那条？
    同时命中两个低价规则是什么意思？

但即使是 retrieval 场景，也必须输出：

1. 具体命中的文档；
2. 具体章节；
3. 具体 chunk；
4. metadata；
5. citation；
6. 命中原因。

不能只输出模型总结。

---

## 14. hybrid 检索预留规范

hybrid 检索是 baseline 和 vector 的组合。

当前 5号窗口至少需要预留 hybrid 能力。

建议支持以下模式：

    baseline
    vector
    hybrid

其中：

- `baseline`：只使用结构化规则打分；
- `vector`：只使用向量相似度；
- `hybrid`：baseline + vector 共同召回和融合。

---

## 15. 最小 hybrid 检索策略

当前阶段建议的最小 hybrid 策略如下：

    baseline 召回 top_k
            ↓
    vector 召回 top_k
            ↓
    合并候选
            ↓
    按 chunk_id 去重
            ↓
    计算 fusion_score
            ↓
    按 final_score 排序
            ↓
    输出统一 retrieval result

不建议当前阶段直接上复杂调参系统。

原因：

1. 5号窗口主任务是规则解释层正式化；
2. hybrid 是增强项，不应压过主链；
3. 复杂融合需要评估样本支撑；
4. 当前验收要求是“有预留或清楚设计”。

---

## 16. hybrid 分数字段预留

建议检索结果中预留以下字段：

    baseline_score
    vector_score
    fusion_score
    rerank_score
    final_score
    score_reasons

如果某种模式未启用，对应字段可以为 null。

例如 baseline-only 模式：

    {
      "baseline_score": 18.5,
      "vector_score": null,
      "fusion_score": 18.5,
      "rerank_score": null,
      "final_score": 18.5
    }

---

## 17. rerank 预留规范

rerank 是对候选结果的二次排序能力。

当前阶段只要求预留，不强制接入复杂 rerank 模型。

建议预留：

1. `rerank_enabled` 配置；
2. `rerank_adapter.py`；
3. `rerank_score` 字段；
4. `rerank_reason` 字段；
5. rerank 前后的结果对比能力。

当前阶段如果不启用 rerank，应明确：

    rerank_enabled = false

retrieval service 必须保证在 rerank 关闭时仍然稳定返回结果。

---

## 18. retrieval result 统一字段

无论 baseline、vector、hybrid，最终都应输出统一结构。

推荐字段：

| 字段名               | 说明           |
|-------------------|--------------|
| `chunk_id`        | 命中的 chunk id |
| `rule_code`       | 规则编码         |
| `rule_version`    | 规则版本         |
| `anomaly_type`    | 异常类型         |
| `doc_title`       | 文档标题         |
| `section_title`   | 章节标题         |
| `section_path`    | 章节路径         |
| `source_doc_path` | 来源文档路径       |
| `chunk_text`      | chunk 正文     |
| `preview_text`    | 预览文本         |
| `metadata`        | metadata     |
| `baseline_score`  | baseline 分数  |
| `vector_score`    | vector 分数    |
| `fusion_score`    | 融合分数         |
| `rerank_score`    | rerank 分数    |
| `final_score`     | 最终分数         |
| `score_reasons`   | 命中原因         |
| `retrieval_mode`  | 检索模式         |

---

## 19. preview_text 规范

`preview_text` 是用于展示的短文本。

建议：

1. 从 `chunk_text` 前部截取；
2. 长度控制在 80 到 200 个中文字符；
3. 不应替代完整 `chunk_text`；
4. citation 可以使用 `preview_text`；
5. evidence 可保留完整或半完整内容。

---

## 20. evidence 构建时 metadata 的使用

evidence 应从 retrieval result 中继承 metadata。

evidence 至少应包含：

    source_table
    source_id
    rule_code
    rule_version
    anomaly_type
    doc_title
    section_title
    section_path
    chunk_id
    preview_text
    score
    score_reasons
    metadata

metadata 在 evidence 中的作用：

1. 说明证据来源；
2. 说明规则归属；
3. 说明命中原因；
4. 支撑后续调试；
5. 支撑 6号窗口编排。

---

## 21. citation 构建时 metadata 的使用

citation 是 evidence 的展示层结果。

citation 至少使用以下 metadata：

    doc_title
    section_title
    section_path
    source_doc_path
    chunk_id
    preview_text

citation 不应包含太多内部检索字段。

例如以下字段通常不直接展示给业务用户：

    baseline_score
    vector_score
    fusion_score
    rerank_score
    metadata_json 全量内容

---

## 22. explanation 场景 metadata 使用流程

explanation 场景推荐流程：

    输入 audit_result_id
            ↓
    查询 audit_result
            ↓
    查询 rule_hit
            ↓
    查询 rule_definition
            ↓
    根据 rule_code / rule_version / anomaly_type 约束 metadata
            ↓
    检索 rule_chunk
            ↓
    生成 retrieval result
            ↓
    生成 evidence
            ↓
    生成 citation
            ↓
    输出 explanation result

关键点：

metadata 是在结果层事实之后使用的，不是在结果层事实之前使用的。

---

## 23. retrieval 场景 metadata 使用流程

retrieval 场景推荐流程：

    输入用户 query
            ↓
    识别 query 中可能的 rule_code / anomaly_type / 关键词
            ↓
    baseline / vector / hybrid 检索 rule_chunk
            ↓
    根据 metadata 过滤 inactive chunk
            ↓
    根据 score 和 score_reasons 排序
            ↓
    输出 retrieval result
            ↓
    生成 citation

retrieval 场景可以直接从 query 出发，但仍必须返回可追溯 metadata。

---

## 24. metadata 过滤规则

默认检索应过滤：

1. `is_active = false` 的 chunk；
2. 与当前 explanation anomaly_type 明显不一致的 chunk；
3. 与当前 rule_code 明显不一致且无 related_rule_codes 关系的 chunk；
4. 文档类型为草稿、测试日志、临时说明的 chunk；
5. source_doc_path 不在正式 RAG 文档范围内的 chunk。

---

## 25. metadata 冲突处理

如果出现 metadata 与结果层事实冲突，例如：

    audit_result.anomaly_type = low_price
    检索结果 metadata.anomaly_type = spec_risk

处理原则：

1. explanation 场景下应过滤或大幅降权；
2. retrieval 场景下可保留，但必须说明命中原因；
3. 如果冲突频繁出现，应检查 chunk metadata 构建逻辑；
4. 不允许直接将冲突结果作为 explanation 的核心证据。

---

## 26. score_reasons 输出规范

每条检索结果应尽量输出 `score_reasons`。

示例：

    [
      "rule_code_exact_match",
      "rule_version_match",
      "anomaly_type_match",
      "chunk_type_priority",
      "keyword_match"
    ]

score_reasons 的作用：

1. 方便调试检索结果；
2. 支撑 evidence 解释；
3. 支撑 6号窗口 trace 展示；
4. 支撑后续测试验证；
5. 提升项目面试可讲性。

---

## 27. 推荐 score_reasons 枚举

| score_reason              | 说明          |
|---------------------------|-------------|
| `rule_code_exact_match`   | 规则编码精确匹配    |
| `rule_code_related_match` | 相关规则编码匹配    |
| `rule_version_match`      | 规则版本匹配      |
| `anomaly_type_match`      | 异常类型匹配      |
| `source_doc_path_match`   | 来源文档匹配      |
| `doc_title_match`         | 文档标题命中      |
| `section_title_match`     | 章节标题命中      |
| `section_path_match`      | 章节路径命中      |
| `keyword_match`           | 关键词命中       |
| `tag_match`               | 标签命中        |
| `chunk_text_match`        | 正文命中        |
| `chunk_type_priority`     | chunk 类型加权  |
| `vector_similarity_match` | 向量语义命中      |
| `active_chunk_filter`     | 启用 chunk 过滤 |
| `manual_review_related`   | 与人工复核流程相关   |
| `faq_related`             | 与 FAQ 相关    |

---

## 28. metadata 构建原则

metadata 应在 chunk 构建阶段生成，而不是每次检索时临时拼。

建议流程：

    读取规则文档
            ↓
    解析文档标题和章节
            ↓
    推断 rule_code / anomaly_type / rule_version
            ↓
    生成 chunk_text
            ↓
    生成 metadata_json
            ↓
    写入 rule_chunk

这样可以保证检索时结构稳定。

---

## 29. metadata 维护原则

metadata 维护应遵守以下原则：

1. 规则文档变更后，应重新构建相关 chunk；
2. `rule_definition` 版本变更后，应检查 metadata.rule_version；
3. source_doc_path 不应频繁变化；
4. section_title 和 section_path 应尽量稳定；
5. 废弃文档应设置 is_active = false；
6. FAQ 类 metadata 应明确 chunk_type = faq；
7. 人工复核类 metadata 应明确 chunk_type = manual_review；
8. 不确定归属的 chunk 不应进入默认 explanation 检索。

---

## 30. 与配置中心的关系

当前阶段建议在配置中预留以下检索参数：

    retrieval_mode = baseline
    retrieval_top_k = 5
    vector_enabled = true
    hybrid_enabled = false
    rerank_enabled = false

如后续启用 hybrid 或 rerank，应通过配置控制，而不是写死在业务代码中。

---

## 31. 与 6号窗口的交接口径

5号窗口完成后，应向 6号窗口交付稳定的 retrieval result。

6号窗口可以使用：

1. `retrieval_mode`
2. `score_reasons`
3. `metadata`
4. `evidence`
5. `citation`

6号窗口不应重新定义：

1. metadata 字段含义；
2. score_reasons 基本枚举；
3. explanation 场景过滤规则；
4. evidence / citation 转换逻辑；
5. baseline / vector / hybrid 的底层实现。

6号窗口的职责是编排，不是重写检索内核。

---

## 32. 验收标准

本文档对应的验收标准如下：

1. 已明确 metadata 是规则检索的结构化锚点；
2. 已明确 metadata 最小字段集合；
3. 已明确 baseline 如何使用 metadata；
4. 已明确 vector 如何使用 metadata；
5. 已明确 hybrid 如何预留 metadata 和分数字段；
6. 已明确 rerank 如何预留字段；
7. 已明确 explanation 场景的 metadata 约束；
8. 已明确 retrieval 场景的 metadata 使用方式；
9. 已明确 score_reasons 规范；
10. 已明确 metadata 如何支撑 evidence；
11. 已明确 metadata 如何支撑 citation；
12. 已明确与 6号窗口的交接口径。

---

## 33. 一句话总结

metadata 是 5号窗口规则检索解释系统的结构化锚点。

它必须让每一次检索结果都能回答：

    命中了哪条规则？
    属于哪个异常类型？
    来自哪份文档？
    来自哪个章节？
    为什么被选中？
    能否作为当前异常解释的依据？

没有 metadata，RAG 就只是文本搜索；有了 metadata，RAG 才能成为可追溯的规则解释系统。