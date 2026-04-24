# Evidence / Citation Schema 规范

## 1. 文档目的

本文档用于定义 5号窗口中 `evidence` 与 `citation` 的正式口径、字段结构、生成来源、转换关系、使用边界，以及它们如何服务规则解释、RAG
检索、统一问答编排和后续人工复核展示。

本文件是 5号窗口：规则解释 / RAG 检索解释窗口 的 source of truth 文档之一。

本文档要解决的问题包括：

- 什么是 evidence；
- 什么是 citation；
- evidence 和 citation 为什么必须分开；
- evidence 至少应包含哪些字段；
- citation 至少应包含哪些字段；
- evidence 可以来自哪些对象；
- citation 如何从 evidence 中生成；
- explanation 场景中如何组织证据；
- retrieval 场景中如何展示引用；
- 6号窗口如何复用 evidence / citation，而不是重新定义一套结构。

一句话：

> evidence 是系统内部证据对象，citation 是面向用户展示的引用对象。二者有关联，但不能混为一谈。

---

## 2. 核心结论

在本项目中：

    evidence：用于支撑回答、解释、测试、编排和追溯的内部证据对象。
    citation：用于对外展示规则来源、文档章节和引用依据的展示对象。

二者关系如下：

    evidence -> citation

也就是说：

1. 先产生 evidence；
2. 再从 evidence 中抽取适合展示的字段生成 citation；
3. citation 不能反向替代 evidence；
4. citation 不能用于反推规则事实；
5. evidence 才是解释链内部真正的证据载体。

---

## 3. 为什么 evidence 和 citation 必须分开

如果不区分 evidence 和 citation，会出现以下问题：

1. 内部证据字段太多，直接展示给用户会很乱；
2. 展示引用字段太少，无法支撑调试和编排；
3. 6号窗口 `/ask` 编排时需要结构化证据，但 UI 只需要引用摘要；
4. 测试时需要判断命中了哪条规则、哪个 chunk、为什么命中，但用户只需要看到来源；
5. 如果 citation 被当成 evidence 使用，就会丢失输入快照、阈值快照、分数、命中原因等关键信息。

因此，本项目必须保持两层结构：

| 对象         | 面向对象 | 主要作用             | 是否包含完整结构化信息 |
|------------|------|------------------|------------:|
| `evidence` | 系统内部 | 支撑解释、编排、测试、追溯    |           是 |
| `citation` | 用户展示 | 展示引用来源、文档章节、依据摘要 |           否 |

---

## 4. evidence 的定位

`evidence` 是用于支撑系统回答和解释的内部证据对象。

它可以来自：

1. `audit_result`
2. `rule_hit`
3. `rule_definition`
4. `rule_chunk`
5. retrieval result
6. explanation service 组装结果

在 explanation 场景中，evidence 应体现完整解释链：

    audit_result -> rule_hit -> rule_definition -> rule_chunk

其中：

- `audit_result` 证据说明最终异常结果；
- `rule_hit` 证据说明具体命中过程；
- `rule_definition` 证据说明规则定义和配置；
- `rule_chunk` 证据说明规则文档依据。

---

## 5. citation 的定位

`citation` 是面向用户展示的引用对象。

它通常来自 `rule_chunk` 类 evidence。

citation 主要用于：

1. `/ask` 回答中的引用来源；
2. UI 页面中的规则依据展示；
3. 报告中的规则引用；
4. 人工复核页面中的“查看规则依据”区域；
5. 面试演示时说明系统解释不是模型瞎编。

citation 不应该承载完整内部信息。

例如以下内容通常不直接放进 citation：

- `input_snapshot`
- `threshold_snapshot`
- `computed_value`
- `baseline_score`
- `vector_score`
- `fusion_score`
- `metadata_json` 全量内容
- 复杂调试字段

这些字段应该保留在 evidence 中。

---

## 6. evidence 的来源类型

建议将 evidence 按来源分为以下类型：

| evidence_type      | 来源对象              | 说明       |
|--------------------|-------------------|----------|
| `audit_result`     | `audit_result`    | 异常结果摘要证据 |
| `rule_hit`         | `rule_hit`        | 规则命中明细证据 |
| `rule_definition`  | `rule_definition` | 规则定义证据   |
| `rule_chunk`       | `rule_chunk`      | 规则文档依据证据 |
| `retrieval_result` | 检索结果              | 检索过程证据   |
| `manual_review`    | 人工复核文档或记录         | 复核流程证据   |

在 5号窗口中，重点先实现：

1. `rule_hit`
2. `rule_definition`
3. `rule_chunk`
4. `retrieval_result`

其中 `rule_chunk` 是 citation 的主要来源。

---

## 7. EvidenceSchema 最小字段集合

`EvidenceSchema` 建议至少包含以下字段：

| 字段名                  | 类型建议                | 是否必需 | 说明                      |
|----------------------|---------------------|-----:|-------------------------|
| `evidence_id`        | string              |    是 | 证据对象 ID，可由类型和来源 ID 组合生成 |
| `evidence_type`      | string              |    是 | 证据类型                    |
| `source_table`       | string              |    是 | 来源表或来源对象                |
| `source_id`          | int / string        |    是 | 来源对象 ID                 |
| `rule_code`          | string / null       |   建议 | 规则编码                    |
| `rule_version`       | string / null       |   建议 | 规则版本                    |
| `anomaly_type`       | string / null       |   建议 | 异常类型                    |
| `doc_title`          | string / null       |   可选 | 文档标题                    |
| `section_title`      | string / null       |   可选 | 章节标题                    |
| `section_path`       | string / null       |   可选 | 章节路径                    |
| `chunk_id`           | int / string / null |   可选 | rule_chunk ID           |
| `source_doc_path`    | string / null       |   可选 | 来源文档路径                  |
| `preview_text`       | string / null       |   可选 | 证据预览文本                  |
| `score`              | float / null        |   可选 | 综合分数                    |
| `score_reasons`      | array               |   可选 | 命中原因                    |
| `metadata`           | object / null       |   可选 | 检索 metadata             |
| `input_snapshot`     | object / null       |   可选 | 输入快照                    |
| `threshold_snapshot` | object / null       |   可选 | 阈值快照                    |
| `computed_value`     | object / null       |   可选 | 计算值                     |
| `trace_note`         | string / null       |   可选 | 追踪说明                    |

---

## 8. EvidenceSchema 字段说明

### 8.1 evidence_id

`evidence_id` 是证据对象的唯一标识。

建议生成方式：

    evidence_id = evidence_type + ":" + source_table + ":" + source_id

示例：

    rule_hit:rule_hit:35
    rule_chunk:rule_chunk:12
    rule_definition:rule_definition:4

---

### 8.2 evidence_type

`evidence_type` 表示证据类型。

推荐取值：

    audit_result
    rule_hit
    rule_definition
    rule_chunk
    retrieval_result
    manual_review

---

### 8.3 source_table

`source_table` 表示证据来源表或来源对象。

示例：

    audit_result
    rule_hit
    rule_definition
    rule_chunk

---

### 8.4 source_id

`source_id` 表示来源对象 ID。

例如：

- `audit_result.id`
- `rule_hit.id`
- `rule_definition.id`
- `rule_chunk.id`

---

### 8.5 rule_code

`rule_code` 表示规则编码。

当前核心规则编码包括：

    LOW_PRICE_EXPLICIT
    LOW_PRICE_STAT
    CROSS_PLATFORM_GAP
    SPEC_RISK

如果 evidence 来源不是单一规则，例如 FAQ 或人工复核流程，`rule_code` 可以为空，但应尽量在 metadata 中说明相关规则。

---

### 8.6 rule_version

`rule_version` 表示规则版本。

它用于说明当前 evidence 对应的是哪版规则。

在 explanation 场景中，应尽量与 `rule_hit` 或 `rule_definition` 中的规则版本一致。

---

### 8.7 anomaly_type

`anomaly_type` 表示异常类型。

当前正式取值：

    low_price
    cross_platform_gap
    spec_risk

不要使用非正式简称，例如：

    gap
    spec
    low

---

### 8.8 doc_title

`doc_title` 表示证据关联的文档标题。

主要用于 `rule_chunk` 类 evidence。

示例：

    低价异常规则说明
    跨平台价差规则说明
    规格识别风险规则说明

---

### 8.9 section_title

`section_title` 表示证据关联的章节标题。

示例：

    显式低价规则
    统计低价规则
    标题规格冲突
    价差比例阈值

---

### 8.10 section_path

`section_path` 表示完整章节路径。

示例：

    低价异常规则说明 > 显式低价规则 > 阈值口径

它比 `section_title` 更适合用于 citation 展示。

---

### 8.11 chunk_id

`chunk_id` 表示命中的 `rule_chunk.id`。

主要用于：

1. 引用定位；
2. 检索结果追溯；
3. smoke test 验证；
4. 6号窗口编排 trace；
5. 7号窗口 UI 展示。

---

### 8.12 source_doc_path

`source_doc_path` 表示来源文档路径。

示例：

    docs/rules/low_price_rules.md

---

### 8.13 preview_text

`preview_text` 是证据预览文本。

建议：

1. 来自 `chunk_text`、`hit_message` 或规则说明；
2. 长度控制在 80 到 200 个中文字符；
3. 用于 UI / citation / 测试输出；
4. 不替代完整正文。

---

### 8.14 score

`score` 是证据综合分数。

可来自：

1. baseline score；
2. vector score；
3. fusion score；
4. rerank score；
5. service 层综合评分。

---

### 8.15 score_reasons

`score_reasons` 表示证据为什么被选中。

示例：

    [
      "rule_code_exact_match",
      "anomaly_type_match",
      "section_title_match"
    ]

这个字段非常重要。

它能说明：

1. 为什么这条证据被选中；
2. 检索结果是否合理；
3. explanation 是否服从结果层事实；
4. 后续调试时为什么命中了某个 chunk。

---

### 8.16 metadata

`metadata` 存储检索相关结构化信息。

它通常来自 `rule_chunk.metadata_json` 或 retrieval result。

---

### 8.17 input_snapshot

`input_snapshot` 表示规则判定时的输入快照。

主要来自 `rule_hit.input_snapshot_json`。

示例可能包括：

    clean_id
    normalized_brand
    normalized_spec
    price
    normalized_platform
    clean_title
    clean_spec

在 explanation 场景中，这个字段非常关键，因为它说明系统当时拿什么输入做了判断。

---

### 8.18 threshold_snapshot

`threshold_snapshot` 表示规则阈值快照。

主要来自 `rule_hit.threshold_snapshot_json` 或 `rule_definition.threshold_config_json`。

示例可能包括：

    explicit_price_threshold
    low_price_ratio_threshold
    cross_platform_gap_threshold

---

### 8.19 computed_value

`computed_value` 表示判定过程中计算出的值。

主要来自 `rule_hit.computed_value_json`。

示例可能包括：

    current_price
    group_avg_price
    price_ratio
    gap_ratio
    platform_count

---

### 8.20 trace_note

`trace_note` 表示证据使用过程中的补充说明。

示例：

    未找到完全匹配规则版本，使用当前启用规则文档。
    当前 evidence 来自 rule_hit，优先级高于 rule_chunk。
    当前 citation 来自 rule_chunk，仅用于文档依据展示。

---

## 9. CitationSchema 最小字段集合

`CitationSchema` 建议至少包含以下字段：

| 字段名               | 类型建议          | 是否必需 | 说明             |
|-------------------|---------------|-----:|----------------|
| `citation_id`     | string        |    是 | 引用 ID          |
| `evidence_id`     | string / null |   建议 | 对应 evidence ID |
| `doc_title`       | string        |    是 | 文档标题           |
| `section_title`   | string        |    是 | 章节标题           |
| `section_path`    | string        |   建议 | 完整章节路径         |
| `chunk_id`        | int / string  |   建议 | 对应 chunk ID    |
| `source_doc_path` | string        |    是 | 来源文档路径         |
| `quoted_preview`  | string        |    是 | 引用预览           |
| `citation_note`   | string / null |   可选 | 引用说明           |
| `rule_code`       | string / null |   建议 | 规则编码           |
| `rule_version`    | string / null |   建议 | 规则版本           |
| `anomaly_type`    | string / null |   建议 | 异常类型           |

---

## 10. CitationSchema 字段说明

### 10.1 citation_id

`citation_id` 是展示引用 ID。

建议生成方式：

    citation_id = "CIT-" + 序号

示例：

    CIT-001
    CIT-002

---

### 10.2 evidence_id

`evidence_id` 用于回指内部证据对象。

citation 是从 evidence 中生成的，因此建议保留这个字段，方便追溯。

---

### 10.3 doc_title

`doc_title` 表示引用来源文档标题。

示例：

    低价异常规则说明

---

### 10.4 section_title

`section_title` 表示引用来源章节标题。

示例：

    显式低价规则

---

### 10.5 section_path

`section_path` 表示完整章节路径。

示例：

    低价异常规则说明 > 显式低价规则 > 阈值口径

---

### 10.6 chunk_id

`chunk_id` 表示引用来源的 rule_chunk ID。

它可以帮助后续 UI 或调试回到具体 chunk。

---

### 10.7 source_doc_path

`source_doc_path` 表示引用来源文件路径。

示例：

    docs/rules/low_price_rules.md

---

### 10.8 quoted_preview

`quoted_preview` 是引用预览文本。

它应简短、可读，不应太长。

建议长度：

    80 到 200 个中文字符

---

### 10.9 citation_note

`citation_note` 是引用说明。

示例：

    该依据来自低价异常规则说明中的显式低价规则章节。
    该依据用于解释当前命中的 SPEC_RISK 规则。
    该依据属于人工复核流程说明，作为补充建议。

---

### 10.10 rule_code / rule_version / anomaly_type

这三个字段用于展示引用和规则之间的关系。

它们不是必须展示给普通业务用户，但建议保留在结构中，方便 6号窗口和 7号窗口复用。

---

## 11. evidence 与 citation 的转换关系

推荐转换流程：

    retrieval result / rule_hit / rule_definition / rule_chunk
            ↓
    EvidenceSchema
            ↓
    CitationSchema

一般情况下：

1. `rule_hit` 类型 evidence 不一定生成 citation；
2. `rule_definition` 类型 evidence 不一定生成 citation；
3. `rule_chunk` 类型 evidence 通常应生成 citation；
4. retrieval result 如果来自 rule_chunk，也可以生成 citation。

---

## 12. evidence 到 citation 的字段映射

| Evidence 字段       | Citation 字段       |
|-------------------|-------------------|
| `evidence_id`     | `evidence_id`     |
| `doc_title`       | `doc_title`       |
| `section_title`   | `section_title`   |
| `section_path`    | `section_path`    |
| `chunk_id`        | `chunk_id`        |
| `source_doc_path` | `source_doc_path` |
| `preview_text`    | `quoted_preview`  |
| `rule_code`       | `rule_code`       |
| `rule_version`    | `rule_version`    |
| `anomaly_type`    | `anomaly_type`    |

citation 不应直接暴露以下字段：

- `input_snapshot`
- `threshold_snapshot`
- `computed_value`
- `metadata` 全量内容
- `baseline_score`
- `vector_score`
- `fusion_score`
- `rerank_score`

---

## 13. explanation 场景中的 evidence 组织方式

explanation 场景必须围绕以下链路组织 evidence：

    audit_result -> rule_hit -> rule_definition -> rule_chunk

建议 evidence 顺序：

1. `audit_result` evidence；
2. `rule_hit` evidence；
3. `rule_definition` evidence；
4. `rule_chunk` evidence；
5. citation list。

也就是说，文档依据 evidence 不能排在结果事实 evidence 前面。

原因：

1. 结果事实优先；
2. 规则命中明细优先；
3. 规则定义优先；
4. 文档说明最后补充。

---

## 14. explanation 场景中 evidence 示例

示例结构：

    {
      "evidence_id": "rule_hit:rule_hit:35",
      "evidence_type": "rule_hit",
      "source_table": "rule_hit",
      "source_id": 35,
      "rule_code": "LOW_PRICE_EXPLICIT",
      "rule_version": "v1",
      "anomaly_type": "low_price",
      "preview_text": "命中显式低价规则：当前价格低于配置阈值。",
      "input_snapshot": {
        "clean_id": 1001,
        "price": 450,
        "normalized_spec": "500ml"
      },
      "threshold_snapshot": {
        "threshold_price": 498
      },
      "computed_value": {
        "current_price": 450
      },
      "score_reasons": [
        "rule_hit_fact"
      ]
    }

---

## 15. rule_chunk evidence 示例

示例结构：

    {
      "evidence_id": "rule_chunk:rule_chunk:12",
      "evidence_type": "rule_chunk",
      "source_table": "rule_chunk",
      "source_id": 12,
      "rule_code": "LOW_PRICE_EXPLICIT",
      "rule_version": "v1",
      "anomaly_type": "low_price",
      "doc_title": "低价异常规则说明",
      "section_title": "显式低价规则",
      "section_path": "低价异常规则说明 > 显式低价规则 > 阈值口径",
      "chunk_id": 12,
      "source_doc_path": "docs/rules/low_price_rules.md",
      "preview_text": "当商品规格为 500ml 单瓶时，若当前价格低于最低维价阈值，则可判定为显式低价异常。",
      "score": 18.5,
      "score_reasons": [
        "rule_code_exact_match",
        "anomaly_type_match",
        "section_title_match"
      ],
      "metadata": {
        "chunk_type": "threshold",
        "is_active": true
      }
    }

---

## 16. citation 示例

示例结构：

    {
      "citation_id": "CIT-001",
      "evidence_id": "rule_chunk:rule_chunk:12",
      "doc_title": "低价异常规则说明",
      "section_title": "显式低价规则",
      "section_path": "低价异常规则说明 > 显式低价规则 > 阈值口径",
      "chunk_id": 12,
      "source_doc_path": "docs/rules/low_price_rules.md",
      "quoted_preview": "当商品规格为 500ml 单瓶时，若当前价格低于最低维价阈值，则可判定为显式低价异常。",
      "citation_note": "该依据用于解释当前命中的 LOW_PRICE_EXPLICIT 规则。",
      "rule_code": "LOW_PRICE_EXPLICIT",
      "rule_version": "v1",
      "anomaly_type": "low_price"
    }

---

## 17. retrieval 场景中的 citation 使用方式

retrieval 场景中，用户直接问规则，例如：

    低价异常是怎么判断的？

系统应返回：

1. 规则回答；
2. retrieval result；
3. evidence list；
4. citation list。

citation 应说明：

- 来自哪份文档；
- 哪个章节；
- 哪个 chunk；
- 引用预览是什么。

retrieval 场景可以没有具体 `audit_result_id`，但 citation 仍必须能追溯到 `rule_chunk`。

---

## 18. explanation 场景中的 citation 使用方式

explanation 场景中，用户问某条异常为什么被判定，例如：

    clean_id=1001 为什么被判低价异常？

系统应先读取：

1. `audit_result`
2. `rule_hit`
3. `rule_definition`

然后再检索 `rule_chunk` 生成 citation。

citation 只能作为文档依据展示，不能替代前面的结果事实。

---

## 19. citation 使用边界

citation 可以用于：

1. `/ask` 回答中的引用展示；
2. UI 中的“规则依据”区域；
3. 报告中的规则来源；
4. 人工复核页面的依据展示；
5. 面试演示时说明解释可追溯。

citation 不允许用于：

1. 重新判定异常；
2. 替代 `rule_hit`；
3. 替代 `rule_definition`;
4. 反向修改 `audit_result`;
5. 作为唯一内部证据对象；
6. 隐藏 evidence 里的重要结构化信息。

---

## 20. evidence 使用边界

evidence 可以用于：

1. explanation service 内部组装；
2. retrieval service 输出；
3. `/ask` 编排层消费；
4. smoke test 验证；
5. RAG 评估样本验证；
6. UI 或报告生成前的数据准备；
7. trace 或 debug 输出。

evidence 不应直接全部展示给普通业务用户。

原因：

1. 字段多；
2. 有内部结构；
3. 包含调试信息；
4. 可能包含输入快照和阈值快照；
5. 展示层应由 citation 或解释摘要承接。

---

## 21. ExplanationSchema 与 evidence / citation 的关系

建议 `ExplanationSchema` 包含：

    audit_result_id
    clean_id
    anomaly_type
    final_summary
    rule_facts
    evidences
    citations
    trace_notes

其中：

- `rule_facts` 用于总结结果层事实；
- `evidences` 用于保存完整证据；
- `citations` 用于展示引用来源；
- `trace_notes` 用于说明版本不一致、fallback、未命中等情况。

---

## 22. ExplanationSchema 示例

示例结构：

    {
      "audit_result_id": 101,
      "clean_id": 1001,
      "anomaly_type": "low_price",
      "final_summary": "该商品被判定为低价异常，主要原因是当前价格低于显式低价阈值。",
      "rule_facts": {
        "hit_rule_code": "LOW_PRICE_EXPLICIT",
        "hit_rule_version": "v1",
        "hit_message": "命中显式低价规则：当前价格=450，阈值=498。"
      },
      "evidences": [],
      "citations": [],
      "trace_notes": [
        "解释链路遵循 audit_result -> rule_hit -> rule_definition -> rule_chunk。"
      ]
    }

---

## 23. evidence 优先级

在 explanation 场景中，evidence 优先级如下：

    audit_result / rule_hit > rule_definition > rule_chunk > FAQ / 人工复核说明

含义：

1. 结果事实优先于规则文档；
2. 规则命中明细优先于自然语言说明；
3. 规则定义优先于 FAQ；
4. 文档引用用于补充解释，不用于覆盖事实。

---

## 24. citation 优先级

citation 优先引用：

1. 与 `rule_hit.rule_code` 一致的 `rule_chunk`；
2. 与 `rule_definition.version` 一致的 `rule_chunk`；
3. 与 `audit_result.anomaly_type` 一致的 `rule_chunk`；
4. 正式规则说明类 chunk；
5. 阈值说明类 chunk；
6. FAQ 或人工复核补充类 chunk。

FAQ 和人工复核 citation 可以作为补充，不应作为核心判定依据。

---

## 25. evidence 缺失处理

如果 explanation 场景中缺少某类 evidence，应按以下原则处理：

### 25.1 缺少 rule_chunk evidence

允许继续输出基于 `audit_result`、`rule_hit`、`rule_definition` 的解释，但应在 `trace_notes` 中记录：

    未找到匹配的 rule_chunk 文档依据，本次解释仅基于结果层事实和规则定义。

### 25.2 缺少 rule_hit evidence

不建议生成完整 explanation。

应返回错误或降级说明：

    当前异常结果缺少 rule_hit 命中明细，无法生成完整证据链解释。

### 25.3 缺少 rule_definition evidence

不建议生成完整 explanation。

应返回错误或降级说明：

    当前规则定义缺失，无法确认规则版本和阈值配置。

### 25.4 缺少 citation

可以返回 evidence，但应提示：

    当前解释具备内部证据，但缺少可展示的文档引用。

---

## 26. 与 baseline / vector / hybrid 的关系

retriever 输出 retrieval result 后，应转换为 evidence。

流程：

    baseline / vector / hybrid retriever
            ↓
    retrieval result
            ↓
    rule_chunk evidence
            ↓
    citation

其中：

- baseline score 应进入 evidence；
- vector score 应进入 evidence；
- fusion score 应进入 evidence；
- score_reasons 应进入 evidence；
- citation 只保留展示所需字段。

---

## 27. 与 rerank 的关系

rerank 只影响证据排序，不改变证据事实。

如果启用 rerank，应在 evidence 中保留：

    original_score
    rerank_score
    final_score
    rerank_reason

如果未启用 rerank，对应字段可以为空。

citation 通常不展示 rerank 信息。

---

## 28. 与 6号窗口的交接口径

5号窗口应向 6号窗口交付：

1. `EvidenceSchema`
2. `CitationSchema`
3. `ExplanationSchema`
4. retrieval result schema
5. evidence 构建逻辑
6. citation 构建逻辑
7. explanation service 输出结构

6号窗口可以：

1. 读取 evidence；
2. 展示 citation；
3. 在 `/ask` 输出中组合自然语言回答；
4. 在 trace 中记录 evidence / citation；
5. 在 mixed 编排中复用 explanation result。

6号窗口不应：

1. 重新定义 evidence 字段含义；
2. 重新定义 citation 字段含义；
3. 用 citation 反推规则事实；
4. 绕开 explanation service 自己拼解释链；
5. 用模型输出覆盖 evidence 中的结果事实。

---

## 29. 与 7号窗口的关系

7号窗口后续可以在人工复核工作台中使用：

1. citation 展示规则依据；
2. evidence 展示内部调试信息；
3. explanation summary 展示异常解释；
4. rule_facts 展示命中事实。

但 7号窗口不应修改 evidence / citation 的底层含义。

---

## 30. smoke test 验证要求

5号窗口 smoke test 至少应验证：

1. low_price explanation 能生成 evidence；
2. cross_platform_gap explanation 能生成 evidence；
3. spec_risk explanation 能生成 evidence；
4. rule_chunk evidence 能生成 citation；
5. citation 能定位到 doc_title / section_title / chunk_id；
6. evidence 中包含 rule_code / rule_version / anomaly_type；
7. explanation 不引用错误异常类型的 citation；
8. 缺少 rule_chunk 时能降级说明；
9. 缺少 rule_hit 时不生成伪解释。

---

## 31. 不通过表现

以下情况视为 evidence / citation 设计不通过：

1. 只返回自然语言解释，没有 evidence；
2. 只返回 citation，没有内部 evidence；
3. citation 无法定位到具体文档；
4. citation 无法定位到 chunk；
5. evidence 中没有 rule_code；
6. evidence 中没有 source_id；
7. explanation 场景中 citation 与 rule_hit 规则不一致；
8. 模型解释覆盖了 evidence 中的规则事实；
9. 6号窗口需要重新解析字符串才能拿到证据字段。

---

## 32. 推荐 Pydantic Schema 命名

后续代码实现时，建议使用以下命名：

    EvidenceSchema
    CitationSchema
    ExplanationSchema
    RuleFactSchema
    RetrievalResultSchema

文件建议落点：

    app/schemas/evidence.py
    app/schemas/citation.py
    app/schemas/explanation.py
    app/schemas/retrieval.py

---

## 33. 验收标准

本文档对应的验收标准如下：

1. 已明确 evidence 是内部证据对象；
2. 已明确 citation 是展示引用对象；
3. 已明确 evidence 和 citation 不能混用；
4. 已明确 EvidenceSchema 最小字段集合；
5. 已明确 CitationSchema 最小字段集合；
6. 已明确 evidence 到 citation 的转换关系；
7. 已明确 explanation 场景的 evidence 组织顺序；
8. 已明确 citation 的使用边界；
9. 已明确缺失 evidence 时的处理方式；
10. 已明确与 baseline / vector / hybrid 的关系；
11. 已明确与 6号窗口的交接口径；
12. 已明确 smoke test 验证要求。

---

## 34. 一句话总结

evidence 是规则解释系统的内部证据链，citation 是面向用户的引用展示层。

5号窗口必须先构建 evidence，再从 evidence 中生成 citation。

解释链必须始终服从：

    audit_result -> rule_hit -> rule_definition -> rule_chunk

不能让 citation 或模型生成内容反向覆盖 4号窗口已经确定的结果层事实。