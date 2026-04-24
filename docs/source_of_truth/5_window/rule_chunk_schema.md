# rule_chunk Schema 规范

## 1. 文档目的

本文档用于定义 `rule_chunk` 的正式定位、字段结构、与 `rule_definition` 的关系、切分粒度、版本口径、唯一性策略，以及在 RAG
检索解释链路中的使用边界。

本文件是 5号窗口：规则解释 / RAG 检索解释窗口 的 source of truth 文档之一。

本文档要解决的问题包括：

- `rule_chunk` 到底是什么；
- `rule_chunk` 和 `rule_definition` 有什么区别；
- `rule_chunk` 和 `audit_result` / `rule_hit` 有什么关系；
- 一个 chunk 最少需要哪些字段；
- chunk 如何定位到规则文档、章节和规则版本；
- chunk 如何服务 baseline 检索、向量检索、evidence 和 citation；
- 5号窗口如何避免让 RAG 反向覆盖 4号窗口的结果层事实。

一句话：

> `rule_chunk` 是规则文档切片资源，服务于 RAG 检索、规则解释和引用展示；它不是异常判定结果，也不是规则引擎本身。

---

## 2. rule_chunk 的定位

`rule_chunk` 是规则文档经过切分后形成的结构化文本片段。

它的核心作用是：

1. 为规则检索提供可召回文本；
2. 为异常解释提供规则文档依据；
3. 为 evidence 提供证据来源；
4. 为 citation 提供可展示引用；
5. 为 6号窗口 `/ask` 编排层提供稳定的规则依据输入；
6. 为 7号窗口人工复核页面展示规则说明提供依据来源。

`rule_chunk` 不负责：

1. 判定商品是否异常；
2. 计算低价阈值；
3. 判断规格是否冲突；
4. 判断跨平台价差是否异常；
5. 覆盖 `audit_result` 的最终结果；
6. 覆盖 `rule_hit` 的命中事实；
7. 替代 `rule_definition` 成为正式规则定义。

---

## 3. 核心解释链路中的位置

5号窗口必须遵守以下解释链路：

    audit_result -> rule_hit -> rule_definition -> rule_chunk

其中：

| 层级    | 对象                | 作用                              |
|-------|-------------------|---------------------------------|
| 结果摘要层 | `audit_result`    | 说明某条商品最终是否异常、异常类型、主命中规则、原因摘要    |
| 命中明细层 | `rule_hit`        | 说明具体命中了哪些规则、输入值是什么、计算值是什么、阈值是什么 |
| 规则定义层 | `rule_definition` | 说明规则编码、规则名称、规则类型、版本、配置、启用状态     |
| 文档依据层 | `rule_chunk`      | 说明对应规则文档中的依据片段、章节、引用来源          |

因此，`rule_chunk` 是解释链路的最后一环。

它负责补充文档依据和自然语言说明，但不能反过来推翻前面三层已经确定的事实。

---

## 4. rule_chunk 与 rule_definition 的关系

`rule_definition` 是正式规则定义。

`rule_chunk` 是规则文档切片。

二者不是同一个对象。

| 对象                | 主要职责                           | 是否参与异常判定 | 是否参与 RAG 解释 |
|-------------------|--------------------------------|---------:|------------:|
| `rule_definition` | 定义规则编码、规则类型、版本、阈值配置、启用状态       |        是 |           是 |
| `rule_chunk`      | 存放规则文档切片、章节路径、文本内容、检索 metadata |        否 |           是 |

推荐关系：

    一个 rule_definition 可以关联多个 rule_chunk。
    一个 rule_chunk 通常归属于一个 rule_definition。
    FAQ 或人工复核类 chunk 可以不强绑定单一 rule_definition，但必须保留 anomaly_type 或 chunk_type 标识。

示例：

| rule_definition.rule_code | rule_chunk.section_title |
|---------------------------|--------------------------|
| `LOW_PRICE_EXPLICIT`      | 显式低价阈值规则                 |
| `LOW_PRICE_STAT`          | 统计低价规则                   |
| `CROSS_PLATFORM_GAP`      | 跨平台价差判定口径                |
| `SPEC_RISK`               | 规格识别风险判定口径               |

---

## 5. rule_chunk 与 audit_result / rule_hit 的关系

`audit_result` 和 `rule_hit` 是 4号窗口产出的结果层事实。

`rule_chunk` 不能绕开它们单独解释异常。

正确关系如下：

1. `audit_result` 先给出最终异常结果摘要；
2. `rule_hit` 给出具体命中规则和命中过程；
3. `rule_definition` 给出正式规则定义和配置；
4. `rule_chunk` 提供规则文档依据和章节引用。

错误做法：

    直接根据 rule_chunk 文本推断商品是否异常。

正确做法：

    根据 audit_result / rule_hit 确认异常事实，再检索对应 rule_chunk 做依据补充。

---

## 6. rule_chunk 最小字段集合

`rule_chunk` 至少应具备以下字段。

| 字段名                  | 类型建议                    | 是否必需 | 说明                   |
|----------------------|-------------------------|-----:|----------------------|
| `id`                 | int / bigint            |    是 | 主键                   |
| `rule_definition_id` | int / bigint / nullable | 建议必需 | 关联 `rule_definition` |
| `rule_code`          | string                  |    是 | 规则编码                 |
| `rule_version`       | string                  |    是 | 规则版本                 |
| `anomaly_type`       | string                  |    是 | 异常类型                 |
| `source_doc_path`    | string                  |    是 | 来源文档路径               |
| `doc_title`          | string                  |    是 | 文档标题                 |
| `section_title`      | string                  |    是 | 当前章节标题               |
| `section_path`       | string                  |    是 | 完整章节路径               |
| `chunk_index`        | int                     |    是 | 当前文档或章节下的 chunk 序号   |
| `chunk_text`         | text                    |    是 | chunk 正文             |
| `chunk_type`         | string                  |    是 | chunk 类型             |
| `keywords_json`      | json / text             | 建议必需 | 关键词列表                |
| `metadata_json`      | json / text             |    是 | 检索 metadata          |
| `is_active`          | bool                    |    是 | 是否启用                 |
| `created_at`         | datetime                |    是 | 创建时间                 |
| `updated_at`         | datetime                |    是 | 更新时间                 |

如果当前数据库表结构已经有部分字段，但不完全一致，应以当前项目实际模型为准逐步补齐，不建议在 5号窗口大范围破坏已有数据模型。

---

## 7. 字段详细说明

### 7.1 id

`id` 是 `rule_chunk` 的主键。

用途：

- 唯一标识一个 chunk；
- 被 evidence 引用；
- 被 citation 引用；
- 供 retrieval service 返回结果使用。

---

### 7.2 rule_definition_id

`rule_definition_id` 用于关联正式规则定义。

说明：

- 对于正式规则说明类 chunk，建议必须关联 `rule_definition`；
- 对于 FAQ、人工复核流程类 chunk，可以允许为空；
- 如果为空，必须通过 `chunk_type`、`anomaly_type`、`metadata_json` 说明其用途。

示例：

| chunk 类型  | rule_definition_id 是否必需 |
|-----------|------------------------:|
| 正式低价规则说明  |                       是 |
| 跨平台价差规则说明 |                       是 |
| 规格风险规则说明  |                       是 |
| FAQ       |                     可为空 |
| 人工复核流程    |                     可为空 |

---

### 7.3 rule_code

`rule_code` 是规则编码。

当前 4号窗口已经确认的初始规则编码包括：

    LOW_PRICE_EXPLICIT
    LOW_PRICE_STAT
    CROSS_PLATFORM_GAP
    SPEC_RISK

`rule_chunk.rule_code` 应尽量与 `rule_definition.rule_code` 保持一致。

如果一个 chunk 服务多个规则，可以在 `metadata_json` 中记录 `related_rule_codes`，但主字段 `rule_code` 建议保留主要归属规则。

---

### 7.4 rule_version

`rule_version` 是规则版本。

用途：

- 保证解释依据尽量与判定时的规则版本一致；
- 支撑后续规则升级；
- 避免旧文档解释新规则。

示例：

    v1
    2026-04-v1
    low_price_v1

推荐当前阶段先使用与 `rule_definition.version` 一致的版本标识。

---

### 7.5 anomaly_type

`anomaly_type` 是异常类型。

当前统一取值：

    low_price
    cross_platform_gap
    spec_risk

不要使用：

    gap
    price_gap
    spec
    low

原因：

异常类型已经由 4号窗口正式收口，5号窗口必须沿用，不得另起命名。

---

### 7.6 source_doc_path

`source_doc_path` 是规则文档路径。

示例：

    docs/rules/low_price_rules.md
    docs/rules/cross_platform_gap_rules.md
    docs/rules/spec_risk_rules.md
    docs/rules/manual_review_rules.md
    docs/rules/rule_faq.md

用途：

- 支撑 citation 展示；
- 支撑文档追溯；
- 支撑 chunk 重建；
- 支撑检索结果定位。

---

### 7.7 doc_title

`doc_title` 是文档标题。

示例：

    低价异常规则说明
    跨平台价差规则说明
    规格识别风险规则说明
    人工复核流程说明
    规则 FAQ

`doc_title` 应来自 Markdown 一级标题或文档 metadata。

---

### 7.8 section_title

`section_title` 是当前 chunk 所属章节标题。

示例：

    显式低价规则
    统计低价规则
    价差比例阈值
    标题规格冲突
    规范化规格缺失

用途：

- 支撑 citation 定位；
- 支撑 baseline 检索加权；
- 支撑 UI 展示；
- 支撑解释输出。

---

### 7.9 section_path

`section_path` 是完整章节路径。

示例：

    低价异常规则说明 > 显式低价规则 > 阈值口径
    规格识别风险规则说明 > 标题规格冲突
    人工复核流程说明 > 复核动作 > 标记误报

用途：

- 比 `section_title` 更准确；
- 支撑深层章节定位；
- 支撑 citation 展示；
- 支撑检索结果解释。

---

### 7.10 chunk_index

`chunk_index` 表示 chunk 在当前文档或当前章节中的序号。

推荐规则：

- 同一文档内从 0 或 1 开始递增；
- 同一重建流程中尽量保持稳定；
- 如果文档内容变化导致 index 改变，应通过 `source_doc_path + section_path + chunk_index` 尽量保持可追溯。

---

### 7.11 chunk_text

`chunk_text` 是 chunk 正文内容。

要求：

1. 内容必须来自正式规则文档；
2. 不应包含无关开发日志；
3. 不应包含临时测试输出；
4. 不应混入未确认业务口径；
5. 不应过短到失去语义；
6. 不应过长到影响检索精度。

建议长度：

    150 到 800 个中文字符之间

当前阶段不强制精确限制，但需要避免极端过短或极端过长。

---

### 7.12 chunk_type

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

其中：

- `rule_text`、`threshold` 优先级最高；
- `faq` 和 `manual_review` 可作为补充说明；
- `note` 不应单独作为核心判定依据。

---

### 7.13 keywords_json

`keywords_json` 用于存储关键词列表。

示例：

    ["低价", "显式阈值", "500ml", "498", "LOW_PRICE_EXPLICIT"]

用途：

- 支撑 baseline 检索；
- 支撑 score_reasons；
- 支撑人工检查；
- 支撑后续搜索优化。

---

### 7.14 metadata_json

`metadata_json` 用于存储检索相关 metadata。

建议包含：

    {
      "rule_code": "LOW_PRICE_EXPLICIT",
      "rule_version": "v1",
      "anomaly_type": "low_price",
      "doc_title": "低价异常规则说明",
      "section_title": "显式低价规则",
      "section_path": "低价异常规则说明 > 显式低价规则",
      "chunk_type": "threshold",
      "source_doc_path": "docs/rules/low_price_rules.md",
      "tags": ["低价", "阈值", "显式规则"],
      "is_active": true
    }

`metadata_json` 是 baseline、vector、hybrid 检索共同依赖的重要字段。

---

### 7.15 is_active

`is_active` 表示当前 chunk 是否启用。

用途：

- 已废弃规则文档可设置为 false；
- 旧版本文档可保留但不进入默认检索；
- 支撑后续规则版本管理。

---

### 7.16 created_at / updated_at

用于记录 chunk 创建和更新时间。

这两个字段服务于：

- 数据追踪；
- 重建审计；
- 后续问题排查；
- 文档更新管理。

---

## 8. chunk 切分粒度

`rule_chunk` 的切分粒度必须服务两个目标：

1. 检索时能准确命中；
2. 引用时能回到明确章节。

推荐切分顺序：

    文档级
        ↓
    Markdown 标题级
        ↓
    段落级
        ↓
    超长段落二次切分

不要直接按固定字符数粗暴切分整个文档。

原因：

- 固定长度切分容易破坏规则语义；
- 标题信息丢失后 citation 不好展示；
- explanation 场景需要准确回到规则章节；
- baseline 检索依赖标题、章节和 metadata。

---

## 9. 推荐切分策略

### 9.1 一级切分：按文档

每份规则文档作为最外层 source。

示例：

    docs/rules/low_price_rules.md

生成的所有 chunk 都应带上：

    source_doc_path = docs/rules/low_price_rules.md
    doc_title = 低价异常规则说明

---

### 9.2 二级切分：按 Markdown 标题

优先按标题层级切分。

示例：

    # 低价异常规则说明
    ## 显式低价规则
    ### 阈值口径

对应 section_path：

    低价异常规则说明 > 显式低价规则 > 阈值口径

---

### 9.3 三级切分：按段落

如果一个章节下有多个自然段，可以按段落切分。

原则：

- 不拆断同一个规则条件；
- 不拆断同一个示例；
- 不拆断同一个阈值说明；
- 不拆断同一个人工复核建议。

---

### 9.4 四级切分：超长段落二次切分

如果段落过长，可以按句子或长度二次切分。

但必须保留：

- `doc_title`
- `section_title`
- `section_path`
- `chunk_index`
- `rule_code`
- `rule_version`
- `anomaly_type`

---

## 10. chunk 唯一性策略

建议使用以下字段组合判断 chunk 唯一性：

    source_doc_path
    section_path
    chunk_index
    rule_code
    rule_version

如果需要生成稳定 chunk key，可以采用：

    chunk_key = hash(source_doc_path + section_path + chunk_index + rule_code + rule_version)

当前阶段不强制要求必须实现 hash key，但建议在 metadata 中预留 `chunk_key`。

---

## 11. chunk 版本管理

`rule_chunk` 的版本管理应尽量与 `rule_definition.version` 对齐。

推荐规则：

1. 如果 chunk 来自正式规则说明文档，应使用对应 `rule_definition.version`；
2. 如果 chunk 来自 FAQ 或人工复核文档，可使用文档自身版本；
3. 如果规则定义升级，相关 chunk 应重新检查；
4. 如果旧 chunk 不再适用，应设置 `is_active = false`；
5. explanation 服务优先引用与命中规则版本一致的 active chunk；
6. 如果找不到版本完全一致的 chunk，应在 evidence 中记录版本不完全匹配提示。

---

## 12. rule_chunk 与 baseline 检索的关系

baseline 检索优先使用 `rule_chunk` 中的结构化字段。

优先级建议：

1. `rule_code` 精确命中；
2. `rule_version` 命中；
3. `anomaly_type` 命中；
4. `source_doc_path` 命中；
5. `doc_title` 命中；
6. `section_title` 命中；
7. `keywords_json` 命中；
8. `chunk_text` 正文命中。

在 explanation 场景中，baseline 检索应优先受以下对象约束：

    audit_result
    rule_hit
    rule_definition

也就是说，baseline 检索不能只看用户问题文本，还要结合结果层事实。

---

## 13. rule_chunk 与向量检索的关系

向量检索可以使用 `rule_chunk` 作为向量化对象。

建议向量化内容不是单独的 `chunk_text`，而是组合以下内容：

    doc_title
    section_title
    section_path
    rule_code
    anomaly_type
    chunk_text

这样可以增强语义召回的稳定性，避免 chunk_text 太短或缺少上下文导致召回漂移。

向量检索在 explanation 场景中只能作为：

1. 补召回；
2. 辅助排序；
3. 兜底增强。

它不能绕开 `audit_result`、`rule_hit`、`rule_definition` 独立决定解释依据。

---

## 14. rule_chunk 与 hybrid 检索的关系

hybrid 检索是 baseline 检索和向量检索的组合。

当前 5号窗口中，hybrid 检索至少应预留以下能力：

1. 支持 baseline-only；
2. 支持 vector-only；
3. 支持 hybrid；
4. 支持结果去重；
5. 支持融合分数；
6. 支持 score_reasons；
7. 支持后续 rerank 接入。

建议当前阶段的最小 hybrid 逻辑：

    baseline 先召回高精度候选
        ↓
    vector 补充语义候选
        ↓
    按 chunk_id 或 chunk_key 去重
        ↓
    简单融合排序
        ↓
    输出统一 retrieval result

完整复杂 hybrid 策略可后续迭代，不建议在主链未稳定前过度扩展。

---

## 15. rule_chunk 与 rerank 的关系

rerank 不直接改变 `rule_chunk` 数据本身。

rerank 只作用于检索结果排序。

当前阶段只要求预留 rerank 接口和字段，不要求强制接入复杂 rerank 模型。

建议预留字段：

    original_score
    baseline_score
    vector_score
    fusion_score
    rerank_score
    final_score
    score_reasons

如果当前阶段未启用 rerank，应明确：

    rerank_enabled = false

并保证 retrieval service 在 rerank 未启用时仍可稳定返回结果。

---

## 16. rule_chunk 与 evidence 的关系

`rule_chunk` 是 evidence 的重要来源之一。

当某个 chunk 被选为解释依据时，应生成 evidence 对象。

evidence 中至少应包含：

    source_table = rule_chunk
    source_id = rule_chunk.id
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

注意：

evidence 不是只来自 `rule_chunk`。

在 explanation 场景中，evidence 也可以来自：

- `audit_result`
- `rule_hit`
- `rule_definition`
- `rule_chunk`

其中 `rule_chunk` 主要提供文档依据。

---

## 17. rule_chunk 与 citation 的关系

citation 是面向展示的引用对象。

`rule_chunk` 是 citation 的主要来源。

citation 中至少应包含：

    citation_id
    doc_title
    section_title
    section_path
    chunk_id
    source_doc_path
    quoted_preview
    citation_note

citation 不应包含过多内部计算信息。

内部计算信息应保留在 evidence 中。

---

## 18. 使用边界

### 18.1 允许的使用方式

`rule_chunk` 可以用于：

1. 规则文档检索；
2. 异常解释依据补充；
3. evidence 构建；
4. citation 展示；
5. 规则 FAQ 问答；
6. 人工复核页面规则依据展示；
7. `/ask` retrieval / explanation 路由调用。

---

### 18.2 禁止的使用方式

`rule_chunk` 不允许用于：

1. 重新判定商品是否异常；
2. 覆盖 `audit_result`；
3. 覆盖 `rule_hit`；
4. 覆盖 `rule_definition.threshold_config_json`；
5. 根据文档片段反向修改规则命中；
6. 让模型基于 chunk 自由生成与规则事实冲突的结论。

---

## 19. explanation 场景使用规则

在 explanation 场景中，`rule_chunk` 的使用流程必须是：

    输入 audit_result_id 或 clean_id
            ↓
    查询 audit_result
            ↓
    查询 rule_hit
            ↓
    查询 rule_definition
            ↓
    根据 rule_code / rule_version / anomaly_type 约束 rule_chunk
            ↓
    生成 evidence
            ↓
    生成 citation
            ↓
    输出 ExplanationSchema

不能使用：

    用户问题 -> 向量检索 rule_chunk -> 直接生成异常解释

原因：

这种方式会绕开结果层事实，容易出现解释漂移。

---

## 20. retrieval 场景使用规则

在 retrieval 场景中，用户可能直接询问规则文档，例如：

    低价异常怎么判断？
    跨平台价差规则是什么？
    规格风险为什么要人工复核？

此时可以直接检索 `rule_chunk`。

但检索结果仍必须返回：

1. chunk id；
2. 文档标题；
3. 章节标题；
4. 章节路径；
5. 规则编码；
6. 异常类型；
7. 命中分数；
8. 命中原因；
9. citation 信息。

---

## 21. mixed 场景使用规则

mixed 场景属于 6号窗口编排职责。

5号窗口只提供：

1. 检索服务；
2. 解释服务；
3. evidence；
4. citation；
5. retrieval result；
6. explanation result。

5号窗口不负责定义 mixed 编排流程。

---

## 22. 推荐首批 rule_chunk 来源

首批建议从以下规则文档构建 `rule_chunk`：

    docs/rules/low_price_rules.md
    docs/rules/cross_platform_gap_rules.md
    docs/rules/spec_risk_rules.md
    docs/rules/manual_review_rules.md
    docs/rules/rule_faq.md

如果项目中已有旧版规则文档，可先映射：

| 旧文档                            | 建议归属     |
|--------------------------------|----------|
| `low_price_detection_rules.md` | 低价异常规则   |
| `cross_platform_gap_rules.md`  | 跨平台价差规则  |
| `spec_normalization_rules.md`  | 规格识别风险规则 |
| `manual_review_process.md`     | 人工复核流程   |
| `faq.md`                       | 规则 FAQ   |

---

## 23. 数据一致性原则

如果 `rule_chunk` 与前面结果层事实发生冲突，处理优先级为：

    audit_result / rule_hit > rule_definition > rule_chunk > FAQ / 补充说明

也就是说：

1. `audit_result` 和 `rule_hit` 是结果层事实；
2. `rule_definition` 是正式规则定义；
3. `rule_chunk` 是文档依据；
4. FAQ 只是补充解释。

如果发现 `rule_chunk` 文档内容长期与 `rule_definition` 冲突，应记录为文档风险，而不是让模型自行选择相信谁。

---

## 24. 当前阶段落地建议

5号窗口当前阶段建议先完成以下内容：

1. 检查当前是否已有 `rule_chunk` 表；
2. 检查当前是否已有 `app/models/rule_chunk.py`；
3. 检查当前是否已有 `app/schemas/rule_chunk.py`；
4. 对照本文档补齐字段口径；
5. 建立 chunk 构建脚本；
6. 建立 metadata 构建逻辑；
7. 建立 baseline 检索；
8. 再接入向量检索；
9. 最后封装 retrieval service 和 rule explanation service。

不要反过来先写向量检索，再回头补 chunk 结构。

---

## 25. 与 6号窗口的交接口径

5号窗口完成后，应向 6号窗口交付可复用的 `rule_chunk` 相关能力，包括：

1. `rule_chunk` 字段口径；
2. `rule_chunk` 与 `rule_definition` 的关系；
3. chunk metadata 规范；
4. baseline 检索输入输出；
5. vector 检索输入输出；
6. hybrid 检索预留方式；
7. evidence / citation 输出结构；
8. retrieval service 调用方式；
9. rule explanation service 调用方式。

6号窗口不应重新定义 `rule_chunk` 字段含义。

6号窗口只应在编排层调用 5号窗口服务。

---

## 26. 验收标准

本文档对应的验收标准如下：

1. 已明确 `rule_chunk` 是规则文档切片资源；
2. 已明确 `rule_chunk` 不参与异常判定；
3. 已明确 `rule_chunk` 与 `rule_definition` 的关系；
4. 已明确 `rule_chunk` 与 `audit_result` / `rule_hit` 的关系；
5. 已明确最小字段集合；
6. 已明确 chunk 切分粒度；
7. 已明确 chunk 版本管理方式；
8. 已明确 metadata 用途；
9. 已明确与 baseline / vector / hybrid / rerank 的关系；
10. 已明确与 evidence / citation 的关系；
11. 已明确 explanation 场景下必须先看结果层事实；
12. 已明确 6号窗口交接口径。

---

## 27. 一句话总结

`rule_chunk` 是规则文档进入 RAG 系统后的正式切片对象。

它必须服务于：

    audit_result -> rule_hit -> rule_definition -> rule_chunk

这条解释链。

它的价值不是重新判定异常，而是让规则解释有文档依据、能被检索、能被引用、能被追溯。