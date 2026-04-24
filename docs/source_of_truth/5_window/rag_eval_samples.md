# RAG 评估样本结构

## 1. 文档目的

本文档用于定义 5号窗口：规则解释 / RAG 检索解释窗口 的 RAG 评估样本结构、评估范围、样本字段、通过标准和不通过表现。

本文档不是最终 8号窗口的完整测试方案，而是 5号窗口在开发检索和解释能力时必须先建立的基础评估口径。

它的目标是验证：

- retrieval 场景是否能正确检索规则文档；
- explanation 场景是否能围绕结果层事实生成解释；
- evidence 是否包含完整证据结构；
- citation 是否能定位到具体文档和章节；
- 检索结果是否能回到 `rule_chunk`；
- 解释层是否服从 `audit_result / rule_hit / rule_definition`；
- 是否避免“数据库说东，知识库说西”。

一句话：

> RAG 评估样本不是为了证明模型说得像，而是为了证明规则解释有依据、能追溯、不漂移。

---

## 2. 评估范围

5号窗口的 RAG 评估主要覆盖两类场景：

1. retrieval 场景；
2. explanation 场景。

---

## 3. retrieval 场景定义

retrieval 场景指用户直接询问规则、制度、流程、FAQ 等内容。

示例：

    低价异常是怎么判断的？
    跨平台价差规则是什么？
    规格识别风险为什么要人工复核？
    同时命中显式低价和统计低价是什么意思？
    业务人员看到异常后应该怎么复核？

retrieval 场景的核心验收目标是：

1. 能命中正确规则文档；
2. 能命中正确 `rule_chunk`；
3. 能返回 metadata；
4. 能返回 score_reasons；
5. 能返回 citation；
6. 不生成脱离文档依据的规则结论。

---

## 4. explanation 场景定义

explanation 场景指用户围绕某条已经判定的异常结果提问。

示例：

    clean_id=1001 为什么被判低价异常？
    audit_result_id=12 的异常依据是什么？
    这条规格风险是怎么来的？
    为什么这个商品命中了 CROSS_PLATFORM_GAP？
    这条低价异常对应哪条规则？

explanation 场景的核心验收目标是：

1. 先读取 `audit_result`；
2. 再读取 `rule_hit`；
3. 再读取 `rule_definition`；
4. 最后检索 `rule_chunk`；
5. 输出 evidence；
6. 输出 citation；
7. 不绕开结果层事实；
8. 不让向量检索反向定义异常原因。

固定解释链路：

    audit_result -> rule_hit -> rule_definition -> rule_chunk

---

## 5. 样本分类

建议将 RAG 评估样本分为以下几类：

| 样本类型                             | 说明                   |
|----------------------------------|----------------------|
| `retrieval_low_price`            | 低价规则检索样本             |
| `retrieval_cross_platform_gap`   | 跨平台价差规则检索样本          |
| `retrieval_spec_risk`            | 规格风险规则检索样本           |
| `retrieval_manual_review`        | 人工复核流程检索样本           |
| `retrieval_faq`                  | FAQ 检索样本             |
| `explanation_low_price`          | 低价异常解释样本             |
| `explanation_cross_platform_gap` | 跨平台价差异常解释样本          |
| `explanation_spec_risk`          | 规格风险异常解释样本           |
| `negative_wrong_rule`            | 错误规则防漂移样本            |
| `fallback_missing_chunk`         | 缺少 rule_chunk 时的降级样本 |

---

## 6. retrieval 样本结构

retrieval 样本用于验证直接规则检索能力。

推荐字段：

| 字段名                       | 是否必需 | 说明             |
|---------------------------|-----:|----------------|
| `case_id`                 |    是 | 样本编号           |
| `case_type`               |    是 | 样本类型           |
| `query`                   |    是 | 用户问题           |
| `expected_rule_codes`     |   建议 | 期望命中的规则编码      |
| `expected_anomaly_type`   |   建议 | 期望命中的异常类型      |
| `expected_doc_keywords`   |   建议 | 期望命中的文档关键词     |
| `expected_chunk_types`    |   可选 | 期望命中的 chunk 类型 |
| `forbidden_rule_codes`    |   可选 | 不应命中的规则编码      |
| `forbidden_anomaly_types` |   可选 | 不应命中的异常类型      |
| `min_top_k_hit`           |   建议 | 期望在 top_k 内命中  |
| `citation_required`       |    是 | 是否要求 citation  |
| `evidence_required`       |    是 | 是否要求 evidence  |
| `notes`                   |   可选 | 样本说明           |

---

## 7. retrieval 样本示例

### 7.1 低价规则检索样本

    {
      "case_id": "RET-LOW-001",
      "case_type": "retrieval_low_price",
      "query": "低价异常是怎么判断的？",
      "expected_rule_codes": ["LOW_PRICE_EXPLICIT", "LOW_PRICE_STAT"],
      "expected_anomaly_type": "low_price",
      "expected_doc_keywords": ["低价", "阈值", "统计", "显式"],
      "expected_chunk_types": ["rule_text", "threshold", "definition"],
      "forbidden_rule_codes": ["SPEC_RISK"],
      "forbidden_anomaly_types": ["spec_risk"],
      "min_top_k_hit": 3,
      "citation_required": true,
      "evidence_required": true,
      "notes": "检索型问题，应命中低价规则相关 chunk。"
    }

---

### 7.2 跨平台价差规则检索样本

    {
      "case_id": "RET-GAP-001",
      "case_type": "retrieval_cross_platform_gap",
      "query": "跨平台价差规则是什么？",
      "expected_rule_codes": ["CROSS_PLATFORM_GAP"],
      "expected_anomaly_type": "cross_platform_gap",
      "expected_doc_keywords": ["跨平台", "价差", "最低价", "平台"],
      "expected_chunk_types": ["rule_text", "definition"],
      "forbidden_rule_codes": ["SPEC_RISK"],
      "forbidden_anomaly_types": ["spec_risk"],
      "min_top_k_hit": 3,
      "citation_required": true,
      "evidence_required": true,
      "notes": "应命中跨平台价差规则文档，不应误召回规格风险作为核心依据。"
    }

---

### 7.3 规格风险规则检索样本

    {
      "case_id": "RET-SPEC-001",
      "case_type": "retrieval_spec_risk",
      "query": "规格识别风险一般什么情况下会命中？",
      "expected_rule_codes": ["SPEC_RISK"],
      "expected_anomaly_type": "spec_risk",
      "expected_doc_keywords": ["规格", "标题规格", "规格列", "缺失", "冲突"],
      "expected_chunk_types": ["rule_text", "definition"],
      "forbidden_rule_codes": ["CROSS_PLATFORM_GAP"],
      "forbidden_anomaly_types": ["cross_platform_gap"],
      "min_top_k_hit": 3,
      "citation_required": true,
      "evidence_required": true,
      "notes": "应命中规格风险规则，重点检查标题规格冲突和规范化规格缺失。"
    }

---

### 7.4 人工复核流程检索样本

    {
      "case_id": "RET-REVIEW-001",
      "case_type": "retrieval_manual_review",
      "query": "业务人员看到异常后应该怎么复核？",
      "expected_rule_codes": [],
      "expected_anomaly_type": null,
      "expected_doc_keywords": ["人工复核", "确认异常", "误报", "备注"],
      "expected_chunk_types": ["manual_review"],
      "forbidden_rule_codes": [],
      "forbidden_anomaly_types": [],
      "min_top_k_hit": 3,
      "citation_required": true,
      "evidence_required": true,
      "notes": "应命中人工复核流程文档，而不是只返回异常规则。"
    }

---

### 7.5 FAQ 检索样本

    {
      "case_id": "RET-FAQ-001",
      "case_type": "retrieval_faq",
      "query": "为什么同一个商品会同时命中显式低价和统计低价？",
      "expected_rule_codes": ["LOW_PRICE_EXPLICIT", "LOW_PRICE_STAT"],
      "expected_anomaly_type": "low_price",
      "expected_doc_keywords": ["显式低价", "统计低价", "同时命中"],
      "expected_chunk_types": ["faq", "rule_text"],
      "forbidden_rule_codes": ["SPEC_RISK"],
      "forbidden_anomaly_types": ["spec_risk"],
      "min_top_k_hit": 5,
      "citation_required": true,
      "evidence_required": true,
      "notes": "应能解释 low_price 双通道命中，不应把规格风险作为主要答案。"
    }

---

## 8. explanation 样本结构

explanation 样本用于验证异常解释能力。

推荐字段：

| 字段名                          | 是否必需 | 说明             |
|------------------------------|-----:|----------------|
| `case_id`                    |    是 | 样本编号           |
| `case_type`                  |    是 | 样本类型           |
| `audit_result_id`            |   建议 | 异常结果 ID        |
| `clean_id`                   |   建议 | 清洗后商品 ID       |
| `anomaly_type`               |    是 | 异常类型           |
| `expected_rule_codes`        |    是 | 期望解释中出现的规则编码   |
| `expected_rule_versions`     |   可选 | 期望规则版本         |
| `expected_evidence_types`    |    是 | 期望 evidence 类型 |
| `expected_citation_required` |    是 | 是否要求 citation  |
| `forbidden_rule_codes`       |   可选 | 不应出现的规则编码      |
| `forbidden_anomaly_types`    |   可选 | 不应出现的异常类型      |
| `must_include_fact_sources`  |    是 | 必须包含的事实来源      |
| `notes`                      |   可选 | 样本说明           |

---

## 9. explanation 样本示例

### 9.1 低价异常解释样本：显式低价

    {
      "case_id": "EXP-LOW-001",
      "case_type": "explanation_low_price",
      "audit_result_id": 101,
      "clean_id": 1001,
      "anomaly_type": "low_price",
      "expected_rule_codes": ["LOW_PRICE_EXPLICIT"],
      "expected_rule_versions": ["v1"],
      "expected_evidence_types": ["audit_result", "rule_hit", "rule_definition", "rule_chunk"],
      "expected_citation_required": true,
      "forbidden_rule_codes": ["SPEC_RISK"],
      "forbidden_anomaly_types": ["spec_risk"],
      "must_include_fact_sources": ["audit_result", "rule_hit", "rule_definition"],
      "notes": "解释型问题必须先基于 audit_result / rule_hit，再引用低价规则文档。"
    }

---

### 9.2 低价异常解释样本：显式 + 统计双命中

    {
      "case_id": "EXP-LOW-002",
      "case_type": "explanation_low_price",
      "audit_result_id": 102,
      "clean_id": 1002,
      "anomaly_type": "low_price",
      "expected_rule_codes": ["LOW_PRICE_EXPLICIT", "LOW_PRICE_STAT"],
      "expected_rule_versions": ["v1"],
      "expected_evidence_types": ["audit_result", "rule_hit", "rule_definition", "rule_chunk"],
      "expected_citation_required": true,
      "forbidden_rule_codes": ["SPEC_RISK"],
      "forbidden_anomaly_types": ["spec_risk"],
      "must_include_fact_sources": ["audit_result", "rule_hit", "rule_definition"],
      "notes": "用于验证 low_price 双通道规则命中时，解释能同时覆盖显式低价和统计低价。"
    }

---

### 9.3 跨平台价差异常解释样本

    {
      "case_id": "EXP-GAP-001",
      "case_type": "explanation_cross_platform_gap",
      "audit_result_id": 201,
      "clean_id": 2001,
      "anomaly_type": "cross_platform_gap",
      "expected_rule_codes": ["CROSS_PLATFORM_GAP"],
      "expected_rule_versions": ["v1"],
      "expected_evidence_types": ["audit_result", "rule_hit", "rule_definition", "rule_chunk"],
      "expected_citation_required": true,
      "forbidden_rule_codes": ["SPEC_RISK"],
      "forbidden_anomaly_types": ["spec_risk"],
      "must_include_fact_sources": ["audit_result", "rule_hit", "rule_definition"],
      "notes": "用于验证跨平台价差异常解释能回到 CROSS_PLATFORM_GAP 规则文档。"
    }

---

### 9.4 规格识别风险解释样本：标题规格冲突

    {
      "case_id": "EXP-SPEC-001",
      "case_type": "explanation_spec_risk",
      "audit_result_id": 301,
      "clean_id": 3001,
      "anomaly_type": "spec_risk",
      "expected_rule_codes": ["SPEC_RISK"],
      "expected_rule_versions": ["v1"],
      "expected_evidence_types": ["audit_result", "rule_hit", "rule_definition", "rule_chunk"],
      "expected_citation_required": true,
      "forbidden_rule_codes": ["CROSS_PLATFORM_GAP"],
      "forbidden_anomaly_types": ["cross_platform_gap"],
      "must_include_fact_sources": ["audit_result", "rule_hit", "rule_definition"],
      "notes": "用于验证标题规格冲突场景的解释，不应误引跨平台价差规则。"
    }

---

### 9.5 规格识别风险解释样本：规范化规格缺失

    {
      "case_id": "EXP-SPEC-002",
      "case_type": "explanation_spec_risk",
      "audit_result_id": 302,
      "clean_id": 3002,
      "anomaly_type": "spec_risk",
      "expected_rule_codes": ["SPEC_RISK"],
      "expected_rule_versions": ["v1"],
      "expected_evidence_types": ["audit_result", "rule_hit", "rule_definition", "rule_chunk"],
      "expected_citation_required": true,
      "forbidden_rule_codes": ["LOW_PRICE_EXPLICIT", "LOW_PRICE_STAT"],
      "forbidden_anomaly_types": ["low_price"],
      "must_include_fact_sources": ["audit_result", "rule_hit", "rule_definition"],
      "notes": "用于验证规格缺失场景解释，不应因为价格字段存在而误引低价规则。"
    }

---

## 10. 负向样本结构

负向样本用于验证系统不会乱召回、不会乱解释、不会把不相关规则当成依据。

推荐字段：

| 字段名                              | 是否必需 | 说明             |
|----------------------------------|-----:|----------------|
| `case_id`                        |    是 | 样本编号           |
| `case_type`                      |    是 | 样本类型           |
| `query`                          |   可选 | 用户问题           |
| `audit_result_id`                |   可选 | 异常结果 ID        |
| `clean_id`                       |   可选 | 清洗后商品 ID       |
| `expected_blocked_rule_codes`    |    是 | 应避免作为核心依据的规则   |
| `expected_blocked_anomaly_types` |    是 | 应避免作为核心依据的异常类型 |
| `failure_condition`              |    是 | 判定失败的条件        |
| `notes`                          |   可选 | 样本说明           |

---

## 11. 负向样本示例

### 11.1 低价解释不应引用规格风险作为核心依据

    {
      "case_id": "NEG-001",
      "case_type": "negative_wrong_rule",
      "audit_result_id": 101,
      "clean_id": 1001,
      "expected_blocked_rule_codes": ["SPEC_RISK"],
      "expected_blocked_anomaly_types": ["spec_risk"],
      "failure_condition": "当 audit_result.anomaly_type = low_price 时，解释结果将 SPEC_RISK 作为核心 citation。",
      "notes": "用于验证 explanation 场景中 metadata 约束是否生效。"
    }

---

### 11.2 规格风险解释不应引用跨平台价差作为核心依据

    {
      "case_id": "NEG-002",
      "case_type": "negative_wrong_rule",
      "audit_result_id": 301,
      "clean_id": 3001,
      "expected_blocked_rule_codes": ["CROSS_PLATFORM_GAP"],
      "expected_blocked_anomaly_types": ["cross_platform_gap"],
      "failure_condition": "当 audit_result.anomaly_type = spec_risk 时，解释结果将 CROSS_PLATFORM_GAP 作为核心 citation。",
      "notes": "用于验证向量检索不会因语义相似而拉错规则。"
    }

---

### 11.3 retrieval 问人工复核不应只返回低价规则

    {
      "case_id": "NEG-003",
      "case_type": "negative_wrong_rule",
      "query": "业务人员看到异常后应该怎么复核？",
      "expected_blocked_rule_codes": [],
      "expected_blocked_anomaly_types": [],
      "failure_condition": "检索结果只返回低价规则 chunk，未返回 manual_review 类型 chunk。",
      "notes": "用于验证人工复核流程文档是否能被正确召回。"
    }

---

## 12. fallback 样本结构

fallback 样本用于验证证据缺失时系统是否能正确降级，而不是生成伪解释。

推荐字段：

| 字段名                 | 是否必需 | 说明       |
|---------------------|-----:|----------|
| `case_id`           |    是 | 样本编号     |
| `case_type`         |    是 | 样本类型     |
| `audit_result_id`   |   可选 | 异常结果 ID  |
| `clean_id`          |   可选 | 清洗后商品 ID |
| `missing_part`      |    是 | 缺失部分     |
| `expected_behavior` |    是 | 期望行为     |
| `notes`             |   可选 | 样本说明     |

---

## 13. fallback 样本示例

### 13.1 缺少 rule_chunk

    {
      "case_id": "FB-001",
      "case_type": "fallback_missing_chunk",
      "audit_result_id": 101,
      "clean_id": 1001,
      "missing_part": "rule_chunk",
      "expected_behavior": "允许基于 audit_result、rule_hit、rule_definition 输出解释，但 trace_notes 中必须说明未找到匹配 rule_chunk 文档依据。",
      "notes": "缺少文档依据时不能假造 citation。"
    }

---

### 13.2 缺少 rule_hit

    {
      "case_id": "FB-002",
      "case_type": "fallback_missing_rule_hit",
      "audit_result_id": 101,
      "clean_id": 1001,
      "missing_part": "rule_hit",
      "expected_behavior": "不应生成完整 explanation，应提示缺少规则命中明细，无法形成完整证据链。",
      "notes": "rule_hit 是命中过程证据，缺少时不能靠模型猜。"
    }

---

### 13.3 缺少 rule_definition

    {
      "case_id": "FB-003",
      "case_type": "fallback_missing_rule_definition",
      "audit_result_id": 101,
      "clean_id": 1001,
      "missing_part": "rule_definition",
      "expected_behavior": "不应生成完整 explanation，应提示缺少规则定义，无法确认规则版本和阈值配置。",
      "notes": "rule_definition 是正式规则定义，不能由 rule_chunk 替代。"
    }

---

## 14. 必测样本清单

5号窗口至少应准备以下样本：

| 编号 | 样本类型              | 最低数量 |
|----|-------------------|-----:|
| 1  | 低价规则 retrieval    |    1 |
| 2  | 跨平台价差 retrieval   |    1 |
| 3  | 规格风险 retrieval    |    1 |
| 4  | 人工复核 retrieval    |    1 |
| 5  | FAQ retrieval     |    1 |
| 6  | 低价异常 explanation  |    2 |
| 7  | 跨平台价差 explanation |    1 |
| 8  | 规格风险 explanation  |    2 |
| 9  | 错误规则防漂移 negative  |    2 |
| 10 | fallback 缺失证据样本   |    2 |

最低建议样本数：

    14 条

如果时间紧，最少也应覆盖：

    low_price explanation
    cross_platform_gap explanation
    spec_risk explanation
    retrieval 规则问答
    negative 错误引用防漂移

---

## 15. 通过标准

RAG 评估通过标准如下。

### 15.1 retrieval 通过标准

retrieval 样本通过，需要满足：

1. top_k 中命中至少一个期望 rule_code 或期望文档；
2. 返回结果包含 `rule_chunk` 信息；
3. 返回结果包含 metadata；
4. 返回结果包含 score_reasons；
5. 返回结果能生成 citation；
6. 不将 forbidden_rule_codes 作为核心答案依据；
7. 不只返回自然语言总结。

---

### 15.2 explanation 通过标准

explanation 样本通过，需要满足：

1. 先读取 `audit_result`；
2. 再读取 `rule_hit`；
3. 再读取 `rule_definition`；
4. 最后读取或检索 `rule_chunk`；
5. 输出 evidence；
6. 输出 citation；
7. evidence 中包含期望 rule_code；
8. evidence 中包含期望 anomaly_type；
9. citation 能定位到 doc_title / section_title / chunk_id；
10. 不引用 forbidden_rule_codes 作为核心依据。

---

### 15.3 negative 通过标准

negative 样本通过，需要满足：

1. 不把禁止规则作为核心 evidence；
2. 不把禁止异常类型作为核心 citation；
3. 如果向量检索召回了不相关规则，应过滤或降权；
4. explanation 场景优先服从结果层事实；
5. 输出中不能出现规则事实冲突。

---

### 15.4 fallback 通过标准

fallback 样本通过，需要满足：

1. 缺少 `rule_chunk` 时，不伪造 citation；
2. 缺少 `rule_hit` 时，不生成完整伪解释；
3. 缺少 `rule_definition` 时，不生成完整伪解释；
4. 降级信息必须进入 trace_notes；
5. 错误或降级响应应清楚说明缺失原因。

---

## 16. 不通过表现

以下情况视为 RAG 评估不通过：

1. 检索结果没有 metadata；
2. 检索结果无法定位到 `rule_chunk`；
3. citation 无法定位到文档或章节；
4. explanation 结果没有 evidence；
5. explanation 绕过 `audit_result / rule_hit / rule_definition`；
6. 低价异常解释引用规格风险作为核心依据；
7. 规格风险解释引用跨平台价差作为核心依据；
8. 缺少 `rule_hit` 时仍然生成看似完整的解释；
9. 缺少 `rule_chunk` 时伪造 citation；
10. 只输出自然语言答案，没有证据结构；
11. 6号窗口需要重新解析大段字符串才能获得证据信息。

---

## 17. 样本文件建议落点

建议后续将结构化样本放在：

    tests/fixtures/rag_eval_samples.json

或：

    data/eval/rag_eval_samples.json

如果当前阶段暂不创建 JSON 文件，也应先保留本文档作为样本结构口径。

---

## 18. smoke test 建议

5号窗口建议提供两个烟雾测试脚本：

    scripts/smoke_test_retrieval.py
    scripts/smoke_test_explanation.py

### 18.1 smoke_test_retrieval.py 应验证

1. 能检索低价规则；
2. 能检索跨平台价差规则；
3. 能检索规格风险规则；
4. 能检索人工复核流程；
5. 返回结果包含 metadata；
6. 返回结果包含 score_reasons；
7. 返回结果能生成 citation。

---

### 18.2 smoke_test_explanation.py 应验证

1. low_price explanation 能生成 evidence；
2. cross_platform_gap explanation 能生成 evidence；
3. spec_risk explanation 能生成 evidence；
4. explanation 能生成 citation；
5. explanation 不引用错误规则；
6. 缺少 rule_chunk 时能降级；
7. 缺少 rule_hit 时不生成伪解释。

---

## 19. 与 evidence / citation 的关系

RAG 评估必须检查 evidence / citation。

retrieval 场景至少应检查：

    retrieval result -> evidence -> citation

explanation 场景至少应检查：

    audit_result -> rule_hit -> rule_definition -> rule_chunk -> evidence -> citation

其中：

- evidence 用于内部验证；
- citation 用于展示引用；
- 两者不能混用；
- citation 不能替代 evidence；
- evidence 必须保留结构化事实。

---

## 20. 与 baseline / vector / hybrid 的关系

评估样本应能分别验证：

1. baseline 检索是否可解释；
2. vector 检索是否能补语义召回；
3. hybrid 检索是否至少有预留；
4. rerank 关闭时系统是否仍可稳定输出；
5. explanation 场景中 vector 不会乱拉证据。

当前阶段重点验收：

    baseline 稳定性
    vector 召回补充能力
    hybrid / rerank 预留清楚

不要求当前阶段完成复杂 rerank 模型评估。

---

## 21. 与 6号窗口的交接口径

5号窗口交给 6号窗口时，应说明：

1. RAG 评估样本结构；
2. retrieval 场景样本；
3. explanation 场景样本；
4. negative 防漂移样本；
5. fallback 降级样本；
6. smoke test 脚本；
7. 当前已通过样本；
8. 当前未覆盖风险。

6号窗口后续接 `/ask` 编排时，应复用这些样本检查：

1. retrieval route 是否仍能命中规则文档；
2. explanation route 是否仍先读结果层事实；
3. mixed route 是否没有打乱 evidence / citation 结构。

---

## 22. 当前阶段最低验收清单

5号窗口完成前，至少要能回答：

1. 低价规则能不能被检索到？
2. 跨平台价差规则能不能被检索到？
3. 规格风险规则能不能被检索到？
4. 人工复核流程能不能被检索到？
5. 某条 low_price 异常能不能被解释？
6. 某条 cross_platform_gap 异常能不能被解释？
7. 某条 spec_risk 异常能不能被解释？
8. explanation 是否包含 evidence？
9. explanation 是否包含 citation？
10. citation 是否能定位到 `rule_chunk`？
11. 是否避免引用错误规则？
12. 缺少关键证据时是否能降级？

---

## 23. 一句话总结

RAG 评估样本的价值，不是证明模型回答流畅，而是证明 5号窗口的规则解释系统具备以下能力：

    能检索
    能解释
    有证据
    能引用
    可追溯
    不漂移
    不覆盖结果层事实

只有这些通过，5号窗口交给 6号窗口的 retrieval service 和 rule explanation service 才算站得住。