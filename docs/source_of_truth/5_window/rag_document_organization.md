# RAG 规则文档组织规范

## 1. 文档目的

本文档用于定义本项目中 RAG 规则文档的组织方式、纳入范围、排除范围、命名规范、版本管理方式，以及规则文档与 `rule_definition`、`rule_chunk`、`audit_result`、`rule_hit` 之间的关系。

本文件是 5号窗口：规则解释 / RAG 检索解释窗口 的 source of truth 文档之一。

它的目标不是描述“怎么让模型回答得更像人”，而是明确：

- 哪些规则文档可以进入 RAG；
- 哪些文档不能进入 RAG；
- 规则文档如何切分为 `rule_chunk`；
- `rule_chunk` 如何关联正式规则定义；
- RAG 解释如何服从 4号窗口已经产出的结果层事实；
- 后续 6号窗口如何稳定复用规则解释能力。

一句话：

> 本项目中的 RAG 不是通用知识问答系统，而是服务于维价审核场景的规则解释与依据追溯系统。

---

## 2. RAG 在本项目中的定位

本项目是面向企业内部维价审核场景的 AI 辅助系统。

RAG 的作用不是让模型自由聊天，也不是做一个“PDF 问答 Demo”，而是为以下场景提供可追溯依据：

1. 解释某条商品为什么被判为低价异常；
2. 解释某条商品为什么被判为跨平台价差异常；
3. 解释某条商品为什么被判为规格识别风险；
4. 回答业务人员关于维价规则、复核流程、异常类型定义的问题；
5. 为 `/ask` 编排层提供可引用的规则依据；
6. 为后续人工复核页面展示规则依据提供结构化证据。

RAG 在本项目中的定位是：

    规则文档依据层

它不负责直接判定商品是否异常，也不负责替代规则引擎做业务判断。

---

## 3. 核心解释链路

5号窗口必须遵守以下解释链路：

    audit_result -> rule_hit -> rule_definition -> rule_chunk

含义如下：

1. 先读取 `audit_result`，确认系统最终异常结果摘要；
2. 再读取 `rule_hit`，确认具体命中规则、输入值、计算值、阈值快照；
3. 再读取 `rule_definition`，确认规则定义、规则版本、规则类型、启用状态、配置阈值；
4. 最后读取或检索 `rule_chunk`，补充规则文档依据、章节引用和自然语言解释。

这条链路不能反过来。

尤其禁止以下做法：

    先向量检索规则文档 -> 再反推商品为什么异常

正确做法必须是：

    先确认结果层事实 -> 再查规则定义 -> 最后查规则文档依据

---

## 4. 可进入 RAG 的文档类型

以下文档可以进入 RAG，并允许被切分为 `rule_chunk`。

### 4.1 低价异常规则说明文档

用于解释低价异常相关规则，包括但不限于：

- 显式低价阈值规则；
- 统计低价规则；
- 不同规格商品的低价判定口径；
- 低价规则命中后的人工复核建议；
- 低价规则的业务解释说明。

对应异常类型：

    low_price

可能关联规则编码：

    LOW_PRICE_EXPLICIT
    LOW_PRICE_STAT

---

### 4.2 跨平台价差异常规则说明文档

用于解释跨平台价差异常规则，包括但不限于：

- 不同平台价格对比口径；
- 平台数量门槛；
- 价差比例阈值；
- 最低价记录标记逻辑；
- 跨平台价差异常的业务含义；
- 价差异常的人工复核建议。

对应异常类型：

    cross_platform_gap

可能关联规则编码：

    CROSS_PLATFORM_GAP

---

### 4.3 规格识别风险规则说明文档

用于解释规格识别风险相关规则，包括但不限于：

- 标题规格与规格列冲突；
- 规范化规格缺失；
- 标题规格识别提示；
- 规格缺失或冲突对价格判定的影响；
- 规格风险的人工复核建议。

对应异常类型：

    spec_risk

可能关联规则编码：

    SPEC_RISK

---

### 4.4 人工复核流程说明文档

用于解释业务人员在看到异常结果后应如何处理，包括但不限于：

- 什么情况下确认异常；
- 什么情况下标记误报；
- 什么情况下需要补充备注；
- 什么情况下需要重新采集证据；
- 什么情况下需要人工查看商品链接或截图；
- 复核状态流转说明。

注意：

人工复核文档可以进入 RAG，但它主要服务于解释和业务操作建议，不参与异常判定。

---

### 4.5 FAQ / 业务解释文档

用于回答业务人员常见问题，例如：

- 为什么同一个商品会同时命中显式低价和统计低价；
- 为什么有些商品没有低价异常但存在规格风险；
- 为什么跨平台价差只标记最低价记录；
- 为什么规格识别风险需要人工复核；
- 为什么模型解释不能覆盖规则引擎结果。

FAQ 文档可以进入 RAG，但必须明确其定位是“解释补充”，不是正式规则定义本身。

---

## 5. 暂不进入 RAG 的文档类型

以下内容暂不进入 RAG。

### 5.1 开发过程草稿

包括：

- 临时讨论记录；
- 未确认的设计草案；
- 已废弃的技术方案；
- 个人备忘录；
- 未被总要求或窗口交接确认的临时想法。

原因：

这些内容不是正式业务依据，进入 RAG 后容易造成解释漂移。

---

### 5.2 旧版脚本注释

旧版脚本注释不能直接作为 RAG 文档依据。

如果旧版脚本中的规则说明仍有价值，必须先整理为正式规则说明文档，再进入 RAG。

原因：

旧脚本可能包含过时字段、旧阈值、临时逻辑或与当前 4号窗口规则引擎不一致的表达。

---

### 5.3 与维价业务无关的 README 内容

README 中关于项目启动、依赖安装、Docker、Git、环境配置等内容，不进入规则解释 RAG。

原因：

这些内容属于工程交付文档，不属于维价规则依据。

---

### 5.4 未确认口径的聊天记录

聊天记录、口头讨论、临时业务反馈，不能直接进入 RAG。

如果其中有正式业务规则，必须先沉淀为 source of truth 文档，再进入 RAG。

---

### 5.5 测试输出日志

例如：

- smoke test 运行日志；
- API 调试返回；
- 数据库临时查询结果；
- 终端错误信息。

这些内容不能进入 RAG。

原因：

测试日志不是规则来源，只能用于验证系统，不应被模型引用为业务依据。

---

## 6. 规则文档建议目录结构

建议规则文档统一放在以下目录中：

    docs/rules/
      low_price_rules.md
      cross_platform_gap_rules.md
      spec_risk_rules.md
      manual_review_rules.md
      rule_faq.md

如后续规则文档继续细分，可以采用：

    docs/rules/
      low_price/
        explicit_low_price.md
        statistical_low_price.md
      cross_platform_gap/
        platform_gap_rules.md
      spec_risk/
        spec_mismatch_rules.md
        missing_spec_rules.md
      review/
        manual_review_process.md
      faq/
        rule_faq.md

但无论目录如何扩展，都必须保证每份文档能明确回答：

- 它服务哪个异常类型；
- 它关联哪些规则编码；
- 它是否可进入 RAG；
- 它是否可被切分为 `rule_chunk`；
- 它是否是正式规则依据。

---

## 7. 文档命名规范

规则文档文件名统一使用英文小写下划线风格。

推荐示例：

    low_price_rules.md
    cross_platform_gap_rules.md
    spec_risk_rules.md
    manual_review_rules.md
    rule_faq.md

不推荐：

    低价规则.md
    低价-rule.md
    gap.md
    规则说明最终版.md
    新建文本文档.md

原因：

1. 便于跨平台路径处理；
2. 便于脚本加载；
3. 便于和 `source_doc_path` 建立稳定关系；
4. 便于后续 Docker / Linux 环境运行。

---

## 8. 文档标题结构规范

进入 RAG 的规则文档建议采用 Markdown 标题结构。

推荐结构：

    # 文档标题

    ## 1. 规则定位

    ## 2. 适用场景

    ## 3. 判定口径

    ## 4. 规则示例

    ## 5. 人工复核建议

    ## 6. 注意事项

对于具体规则文档，可以进一步细分：

    # 低价异常规则说明

    ## 1. 低价异常定义

    ## 2. 显式低价规则

    ### 2.1 规则编码

    ### 2.2 阈值口径

    ### 2.3 命中说明

    ## 3. 统计低价规则

    ### 3.1 规则编码

    ### 3.2 分组口径

    ### 3.3 命中说明

    ## 4. 人工复核建议

标题结构会影响 `section_title` 和 `section_path` 的生成，因此标题必须稳定，不要频繁随意改名。

---

## 9. 文档与 rule_definition 的关联方式

规则文档不直接等同于 `rule_definition`。

二者关系如下：

    rule_definition：正式规则定义，服务规则引擎和结果层事实。
    rule_chunk：规则文档切片，服务 RAG 检索和解释引证。

建议建立以下关联口径：

| 对象 | 作用 | 是否参与异常判定 | 是否参与解释 |
|---|---|---:|---:|
| `rule_definition` | 正式规则定义 | 是 | 是 |
| `rule_chunk` | 规则文档切片 | 否 | 是 |
| `audit_result` | 异常结果摘要 | 是 | 是 |
| `rule_hit` | 规则命中明细 | 是 | 是 |

规则文档进入 RAG 后，应通过 `rule_chunk` 关联到 `rule_definition`，关联字段至少包括：

    rule_definition_id
    rule_code
    rule_version
    anomaly_type
    source_doc_path

---

## 10. 规则文档与异常类型的关系

当前正式异常类型统一为：

    low_price
    cross_platform_gap
    spec_risk

规则文档必须尽量明确自己服务的异常类型。

示例：

| 文档 | anomaly_type | 可能关联 rule_code |
|---|---|---|
| `low_price_rules.md` | `low_price` | `LOW_PRICE_EXPLICIT` / `LOW_PRICE_STAT` |
| `cross_platform_gap_rules.md` | `cross_platform_gap` | `CROSS_PLATFORM_GAP` |
| `spec_risk_rules.md` | `spec_risk` | `SPEC_RISK` |
| `manual_review_rules.md` | 可为空或多类型 | 可为空或多规则 |
| `rule_faq.md` | 可为空或多类型 | 可为空或多规则 |

注意：

`manual_review_rules.md` 和 `rule_faq.md` 可能不是单一异常类型文档，但进入 RAG 时仍应尽量通过 metadata 标记其适用范围。

---

## 11. 规则文档版本管理口径

规则解释必须尽量与判定时使用的规则版本保持一致。

因此，规则文档需要保留版本口径。

建议在规则文档头部维护基础信息：

    ---
    doc_id: low_price_rules
    doc_title: 低价异常规则说明
    rule_codes:
      - LOW_PRICE_EXPLICIT
      - LOW_PRICE_STAT
    anomaly_type: low_price
    version: v1
    is_active: true
    ---

如果当前阶段暂不实现 YAML front matter 解析，也应在文档内容或 metadata builder 中补齐这些信息。

版本管理原则：

1. 规则文档版本应尽量与 `rule_definition.version` 对齐；
2. 如果规则定义更新，相关规则文档也应同步检查；
3. 如果规则文档只是解释补充，不影响判定，也应在 metadata 中标注当前文档版本；
4. 解释服务应优先引用与当前命中规则版本一致的 `rule_chunk`；
5. 如果找不到完全匹配版本，应在 evidence 或 trace note 中标明“未找到完全匹配版本，使用当前启用文档”。

---

## 12. 文档进入 RAG 的流程

规则文档进入 RAG 的推荐流程如下：

    确认文档属于正式规则说明
            ↓
    确认文档命名和标题结构符合规范
            ↓
    确认文档可关联 anomaly_type / rule_code / rule_version
            ↓
    通过 rule_doc_loader 读取文档
            ↓
    通过 rule_chunk_builder 切分 chunk
            ↓
    通过 chunk_metadata_builder 生成 metadata
            ↓
    写入 rule_chunk
            ↓
    由 baseline/vector/hybrid retriever 使用
            ↓
    由 evidence/citation 输出解释依据

其中，写入 `rule_chunk` 后，规则文档才算正式进入 RAG 检索解释体系。

---

## 13. RAG 检索时的文档优先级

在 explanation 场景中，文档优先级应遵守以下规则：

1. 优先引用与当前 `rule_hit.rule_code` 一致的规则文档；
2. 优先引用与当前 `rule_definition.version` 一致的文档；
3. 优先引用与当前 `audit_result.anomaly_type` 一致的文档；
4. 优先引用正式规则说明文档；
5. FAQ 和人工复核文档只能作为补充解释，不应替代正式规则文档；
6. 如果 baseline 与 vector 结果冲突，应优先相信强 metadata 匹配结果。

---

## 14. explanation 场景的文档使用边界

在 explanation 场景中，RAG 只做三件事：

1. 找到与当前异常结果相关的规则文档依据；
2. 为解释输出提供 evidence；
3. 为用户展示生成 citation。

RAG 不做以下事情：

1. 不重新计算价格异常；
2. 不重新判断商品规格；
3. 不覆盖 `audit_result` 的最终结果；
4. 不覆盖 `rule_hit` 的命中事实；
5. 不自行修改 `rule_definition`；
6. 不根据文档内容反向推翻规则引擎结果。

---

## 15. retrieval 场景的文档使用边界

在 retrieval 场景中，用户可能直接询问规则或流程，例如：

    低价异常是怎么判断的？
    跨平台价差规则是什么？
    规格风险为什么要人工复核？

这类问题可以直接走规则文档检索。

但即便如此，回答也应尽量返回：

- 命中的规则文档；
- 命中的章节；
- 命中的 chunk；
- 命中原因；
- citation 信息。

retrieval 场景可以更依赖 query 语义，但仍不能生成脱离文档依据的规则结论。

---

## 16. mixed 场景的文档使用边界

mixed 场景属于 6号窗口编排层职责。

5号窗口只提供可被 mixed 编排调用的能力，例如：

- 根据 query 检索规则文档；
- 根据 `audit_result_id` 解释异常；
- 返回 evidence；
- 返回 citation。

5号窗口不负责定义 mixed 流程，也不负责 `/ask` 的总编排。

---

## 17. 文档维护原则

规则文档维护必须遵守以下原则：

1. 文档变更必须尽量同步检查 `rule_definition`；
2. 规则口径变更必须记录版本；
3. 已废弃文档不得继续作为 active RAG 文档；
4. 旧文档如需保留，应标记为 inactive 或 archived；
5. 进入 RAG 的文档必须有明确业务用途；
6. 文档标题不要频繁无意义改动；
7. 文档内容应避免和当前规则引擎口径冲突；
8. 如果文档和数据库规则定义冲突，以 `rule_definition` 和 4号窗口结果层事实为准。

---

## 18. 当前推荐的首批 RAG 文档

5号窗口首批建议纳入以下文档：

    docs/rules/low_price_rules.md
    docs/rules/cross_platform_gap_rules.md
    docs/rules/spec_risk_rules.md
    docs/rules/manual_review_rules.md
    docs/rules/rule_faq.md

如果当前项目中已有旧版规则文档，可先映射为：

| 旧文档 | 建议新文档 |
|---|---|
| `low_price_detection_rules.md` | `low_price_rules.md` |
| `cross_platform_gap_rules.md` | `cross_platform_gap_rules.md` |
| `spec_normalization_rules.md` | `spec_risk_rules.md` |
| `manual_review_process.md` | `manual_review_rules.md` |
| `faq.md` | `rule_faq.md` |

是否重命名由实际工程情况决定。

若暂不重命名，也必须在 metadata 中统一文档标题和规则归属。

---

## 19. 不一致处理原则

如果出现以下冲突：

    规则文档说 A
    rule_definition 说 B
    rule_hit 实际命中 C
    audit_result 最终摘要 D

处理优先级为：

    audit_result / rule_hit > rule_definition > rule_chunk / 规则文档 > FAQ / 补充说明

解释服务应优先服从结果层事实。

如果发现规则文档长期与 `rule_definition` 不一致，应记录为文档口径风险，而不是让模型自行选择相信谁。

---

## 20. 与 6号窗口的交接口径

5号窗口完成后，应向 6号窗口交付：

1. 规则文档组织规范；
2. `rule_chunk` schema；
3. metadata 规范；
4. baseline / vector / hybrid 检索能力；
5. evidence / citation schema；
6. retrieval service；
7. rule explanation service；
8. RAG 评估样本结构。

6号窗口可以直接调用 5号窗口服务，但不应重新定义：

- 哪些文档可以进入 RAG；
- `rule_chunk` 的字段含义；
- evidence / citation 的区别；
- explanation 的事实优先级；
- RAG 证据选择原则。

---

## 21. 验收标准

本文档对应的验收标准如下：

1. 已明确 RAG 在本项目中不是通用问答，而是规则解释系统；
2. 已明确哪些文档可以进入 RAG；
3. 已明确哪些文档不能进入 RAG；
4. 已明确规则文档与 `rule_definition` 的关系；
5. 已明确规则文档与 `rule_chunk` 的关系；
6. 已明确 explanation 场景必须服从结果层事实；
7. 已明确 retrieval 场景必须返回可追溯依据；
8. 已明确文档版本与规则版本的基本关系；
9. 已明确与 6号窗口的交接口径。

---

## 22. 一句话总结

本项目中的 RAG 规则文档不是给模型自由发挥用的知识库，而是围绕维价审核规则、异常判定结果和人工复核流程建立的可追溯依据层。

它必须服务于：

    audit_result -> rule_hit -> rule_definition -> rule_chunk

这条解释链，而不能反过来覆盖 4号窗口已经确定的异常事实。