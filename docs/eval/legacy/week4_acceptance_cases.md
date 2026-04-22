# 第四周验收用例

## 一、第四周目标

第四周的核心目标不是继续补底层能力，而是把前几周已经完成的能力整合成统一问答入口，使系统能够根据用户问题自动路由到对应工具，并返回结构化结果。

统一入口当前支持四类问题：

1. 数据分析类（analysis）
2. 规则检索类（retrieval）
3. 异常解释类（explanation）
4. 混合问答类（mixed）

---

## 二、验收标准

本周验收重点不看前端，不看 LangGraph，而是看统一 `/ask` 入口是否已经具备以下能力：

- 能正确识别问题类型
- 能调用对应工具
- 能返回统一结构结果
- 能输出工具调用 trace
- 能支持最基础的简短汇报生成
- 能把问答过程写入日志文件

---

## 三、验收用例

### A组：数据分析类

#### A-01 近7天哪个平台异常低价最多？
**问题：**
近7天哪个平台异常低价最多？

**预期：**
- route = analysis
- 调用 analysis_tools
- 返回平台维度的异常低价统计结果
- trace 中应包含 route_query 和 analysis_tools

---

### B组：规则检索类

#### B-01 如果标题不完整，规则上该怎么处理？
**问题：**
如果标题不完整，规则上该怎么处理？

**预期：**
- route = retrieval
- 调用 retrieval_tools
- 返回规格归一 / 规格风险相关规则摘要
- trace 中应包含 route_query 和 retrieval_tools

---

### C组：异常解释类

#### C-01 为什么这个商品会被判成高风险？
**问题：**
为什么这个商品会被判成高风险？

**预期：**
- route = explanation
- 调用 explanation_tools
- 返回结果层事实解释 + 规则层依据 + 复核建议
- rule_query 不应停留在“高风险”这种泛问句，而应尽量改写为更适合规则检索的具体问句
- trace 中应包含 route_query 和 explanation_tools

---

### D组：混合问答类

#### D-01 先找出低价商品，再按规则给我写一段简短汇报
**问题：**
先找出低价商品，再按规则给我写一段简短汇报。

**预期：**
- route = mixed
- 依次调用 analysis_tools、retrieval_tools、report_tools
- 返回低价样本摘要 + 规则依据摘要 + 复核建议
- trace 中应完整记录 4 步：
  1. route_query
  2. analysis_tools
  3. retrieval_tools
  4. report_tools

---

## 四、附加验收点

### E-01 统一返回结构
所有 `/ask` 返回结果都应尽量保持统一结构，至少包含：

- route
- answer
- tools_used
- analysis_result
- retrieval_result
- explanation_result
- trace

---

### E-02 问答日志落盘
每次调用 `/ask` 后，应将核心信息写入：

`data/outputs/ask_logs.jsonl`

日志中至少应包含：

- timestamp
- question
- route
- tools_used
- answer
- trace

---