## 第五周：上前端与工作流骨架，让项目更像系统

### 本周目标

第五周的重点不再是继续扩底层能力，而是把前四周已经形成的能力真正接成一个“可演示、可视化、可讲解”的系统原型。

这一周主要完成两件事：

1. 新增 Streamlit 页面，让统一问答能力可以直接在页面中展示
2. 新增轻量 workflow 骨架，把系统链路表达成更清晰的节点流程

一句话总结：

> 第五周把项目从“后端能力集合”推进成了“可直接演示的 Copilot 系统页面”。

---

### 第五周新增内容

#### 1. 新增 Streamlit 页面

新增文件：

- `app/ui/streamlit_app.py`

当前页面已支持：

- 输入自然语言问题
- 调用 `/ask` 主链路
- 调用 `/ask-lc` LangChain 展示链路
- 切换 `baseline / faiss` 检索模式
- 设置 `top_k`
- 控制是否返回 `trace`

页面当前可展示的内容包括：

- 最终回答
- 问题路由类型
- 调用工具列表
- 数据分析结果区
- 规则证据片段区
- 异常解释区
- 工具调用链路区
- 原始 JSON 调试区

#### 2. 新增一键生成简短汇报

在 Streamlit 页面中新增“生成简短汇报”按钮。

该功能当前基于 `/ask` 的 mixed 场景实现，能够完成：

- 先找出异常或低价样本
- 再检索相关规则依据
- 最后生成一段简短业务汇报

这使得系统不再只是“回答问题”，而是具备了初步业务说明能力。

#### 3. 新增最近问答日志预览

页面中新增最近问答日志预览区，读取：

- `data/outputs/ask_logs.jsonl`

当前可展示最近若干条问答记录，包括：

- 时间
- 路由类型
- 用户问题
- 调用工具
- 回答摘要

这一步增强了系统的“可追踪性”和“演示感”。

#### 4. 补齐 retrieval 分支日志落盘

第四周的 `/ask` 已经具备日志落盘能力，但 retrieval 分支此前未补齐日志写入。

第五周已修复该问题，使以下场景都可以正常落盘：

- analysis
- retrieval
- explanation
- mixed
- unknown

这保证了统一入口各类问题都有一致的日志记录能力。

#### 5. 新增轻量 workflow 骨架

新增文件：

- `app/graph/workflow.py`

这一版 workflow 不是正式 LangGraph 图实现，而是“LangGraph 思维的轻量表达版”。

当前已将系统主链路拆成节点：

- `route_query_node`
- `run_analysis_node`
- `run_retrieval_node`
- `run_explanation_node`
- `compose_answer_node`
- `human_review_node`

并通过 `run_workflow()` 串起受控流程。

---

### 第五周当前工作流设计

当前工作流分为几类：

#### analysis

- route
- analysis
- compose answer
- human review

#### retrieval

- route
- retrieval
- compose answer
- human review

#### explanation

- route
- explanation
- compose answer
- human review

#### mixed

- route
- analysis
- retrieval
- compose answer
- human review

这里最重要的设计取舍是：

> mixed 场景继续采用受控流程，而不是完全依赖自由 agent 决定步骤。

原因是 mixed 问题通常具有更强的业务顺序约束，例如：

- 先看事实结果
- 再找规则依据
- 最后组织汇报

这种场景如果全部交给自由 agent，容易出现流程漂移、问题改写或证据错配。

---

### 第五周设计取舍

#### 1. `/ask` 仍然是主演示链路

当前 `/ask` 仍然是更稳定、更可控的统一入口，适合作为系统页面的主调用链。

#### 2. `/ask-lc` 作为 LangChain 展示副线

`/ask-lc` 当前已经可以展示 LangChain tool calling 能力，但返回结构与稳定性仍不如 `/ask` 统一，因此更适合作为“LangChain
能力展示入口”。

#### 3. 第五周先落 workflow 骨架，不重上 LangGraph 框架

第五周优先完成的是：

- 节点拆分
- 状态流动
- 受控流程表达
- human review 节点预留

而不是直接重度引入 LangGraph 状态图框架。

这样做的原因是：

- 先保证系统展示完整
- 先保证主链路稳定
- 先把流程设计讲清楚

后续再把这一版轻量 workflow 升级到正式 LangGraph，会更自然。

---

### 第五周验收结果

截至第五周，项目已经可以完成以下演示：

1. 在 Streamlit 页面中直接提问
2. 展示 analysis / retrieval / explanation 三类结果
3. 展示规则证据片段和工具调用链路
4. 一键生成 mixed 场景简短汇报
5. 查看最近问答日志
6. 通过 `workflow.py` 跑通轻量受控流程

一句话总结：

> 第五周已经把项目从“后端问答能力”推进成了“可直接展示给面试官和业务方看的系统页面 + 流程骨架”。

---

### 后续优化方向

- 将轻量 workflow 升级为正式 LangGraph 状态图
- 增加文件上传与规则重建索引闭环
- 优化 chunk 预览文本与 section 对齐问题
- 增加测试用例与自动化验证
- 补充 Dockerfile 和部署说明
- 增强前端页面交互与展示细节