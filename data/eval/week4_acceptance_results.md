# 第四周验收结果

## 一、验收结论

第四周第一版统一问答入口已完成基础验收。

当前系统已经能够将前几周形成的分析、规则检索、异常解释和汇报生成能力整合到统一 `/ask` 入口中，并根据问题类型自动路由到不同工具，返回结构化结果和 trace，同时支持最基础的日志落盘。

当前结论：

**第四周第一版验收通过。**

---

## 二、分组验收结果

### A组：数据分析类

#### A-01 近7天哪个平台异常低价最多？
**结果：通过**

**实际表现：**
- route 正确识别为 `analysis`
- tools_used 为 `["analysis_tools"]`
- answer 返回“共统计 30 条记录。异常低价数量最多的平台为 拼多多，共 7 条。”
- analysis_result 中返回了平台统计表
- trace 中正确记录了：
  - route_query
  - analysis_tools

**结论：**
数据分析类问题主链已打通。

---

### B组：规则检索类

#### B-01 如果标题不完整，规则上该怎么处理？
**结果：通过**

**实际表现：**
- route 正确识别为 `retrieval`
- tools_used 为 `["retrieval_tools"]`
- topic 命中“规格归一与规格风险规则”
- 最相关证据命中 FAQ 中“如果标题不完整，规则上该怎么处理？”章节
- trace 中正确记录了：
  - route_query
  - retrieval_tools

**结论：**
规则检索类问题主链已打通。

---

### C组：异常解释类

#### C-01 为什么这个商品会被判成高风险？
**结果：通过（已优化）**

**初始问题：**
最开始 explanation 路径虽然能跑通，但规则检索直接使用用户原问题“为什么这个商品会被判成高风险？”，导致规则层更容易命中 FAQ / 通用规则，规则依据不够聚焦。

**优化动作：**
对 explanation_tools 中的 rule_query 生成逻辑做了优化：
- 对“高风险 / 异常”这类泛解释问句，不再直接用用户原句检索
- 优先根据结果层 facts 自动改写为更具体的规则问题
- 例如改写为：
  - 为什么这个商品会被判成疑似异常低价？
  - 统计低价规则是怎么定义的？

**优化后表现：**
- route 正确识别为 `explanation`
- tools_used 为 `["explanation_tools"]`
- rule_query 已被改写为更具体的低价规则问题
- topic 命中“低价异常规则”
- 规则层依据优先命中《疑似异常低价判定规则说明》
- 最终 explanation 能输出：
  - 结果层事实
  - 规则层摘要
  - 复核建议

**结论：**
异常解释类问题主链已打通，且规则依据命中精度已完成第一轮优化。

---

### D组：混合问答类

#### D-01 先找出低价商品，再按规则给我写一段简短汇报
**结果：通过（已优化）**

**初始表现：**
mixed 主链能够正确执行：
- analysis_tools
- retrieval_tools
- generate_summary

后续为了让系统更像真正的工具分层结构，将汇报生成逻辑从 routes_ask.py 中拆出，独立形成 report_tools。

**第一次拆分后问题：**
report_tools 初版中对 retrieval_result 的证据判断有误，导致 answer 中错误出现：
“当前暂未检索到高相关的低价异常规则依据。”

**修复动作：**
修正 report_tools 中的 retrieval 摘要逻辑，确保：
- 只要 evidences 非空，就视为已检索到规则依据
- 优先选择非 FAQ 文档作为主依据
- 再组织成汇报语言

**修复后表现：**
- route 正确识别为 `mixed`
- tools_used 为：
  - analysis_tools
  - retrieval_tools
  - report_tools
- answer 已正确输出：
  - 低价样本摘要
  - 规则依据摘要
  - 复核建议
- trace 正确记录了：
  1. route_query
  2. analysis_tools
  3. retrieval_tools
  4. report_tools

**结论：**
混合问答类主链已打通，汇报生成已完成工具化拆分。

---

## 三、附加验收结果

### E-01 统一返回结构
**结果：通过**

当前 `/ask` 返回结果已基本统一，包含以下主要字段：

- route
- answer
- tools_used
- analysis_result
- retrieval_result
- explanation_result
- trace

说明第四周统一入口的响应结构已经建立。

---

### E-02 问答日志落盘
**结果：通过**

当前已实现将 `/ask` 的核心执行信息写入：

`data/outputs/ask_logs.jsonl`

日志中已包含：

- timestamp
- question
- route
- tools_used
- answer
- analysis_result / retrieval_result / explanation_result
- trace

说明第四周“记录工具调用日志”这一目标已完成第一版落地。

---

## 四、第四周收口总结

第四周没有继续扩底层能力，而是将前几周已有能力整合为统一问答入口，当前已经完成以下能力闭环：

- 数据分析问答
- 规则检索问答
- 异常解释问答
- 混合问答与简短汇报
- 统一响应结构
- 工具调用 trace
- 问答日志落盘

一句话总结：

**项目已从“多个独立能力模块”升级为“具备统一 ask 入口的 Copilot 原型”。**

---

## 五、后续可优化方向

当前版本已通过第一轮验收，但仍有后续优化空间：

1. 将日志中的 NaN 进一步统一转为更标准的 null
2. 让 report_tools 的输出更像业务日报/周报口吻
3. 为 retrieval 增加 baseline / FAISS 可切换模式
4. 后续引入 LangChain 做工具编排增强
5. 在第五周前端中展示 evidence 与 trace

---