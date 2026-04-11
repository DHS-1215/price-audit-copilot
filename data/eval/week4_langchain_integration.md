# 第四周 LangChain 接入记录

## 一、接入背景

第四周原始计划中，除了完成统一 ask 入口外，还要求进一步使用 LangChain 做工具化封装，使系统能够从“手写编排版统一入口”进一步升级为“具备正式工具调度能力的 Copilot 原型”。

在实际推进过程中，项目先完成了手写编排版 `/ask` 统一入口，主要原因是前几周已经形成了较完整的业务能力模块，包括：

- 数据分析能力
- 规则检索能力
- 异常解释能力
- 简短汇报能力

因此，第四周前半段优先完成了以下目标：

- 统一 ask 入口
- analysis / retrieval / explanation / mixed 四类问题路由
- trace 记录
- ask_logs.jsonl 落盘日志
- baseline / FAISS 可切换检索

在此基础上，第四周后半段补充 LangChain 正式接入，作为“工具调度层”的增强版本。

---

## 二、接入目标

本次 LangChain 接入的目标，不是推翻已经稳定运行的手写编排版 `/ask`，而是：

1. 将现有业务函数正式包装为 LangChain tools
2. 新增一个 LangChain 调度入口 `/ask-lc`
3. 让模型能够基于问题类型自动决定调用分析、检索、解释或汇报工具
4. 验证 LangChain 在本项目中的适用性与稳定性
5. 观察自由 agent 在不同业务场景下的表现差异

一句话概括：

**在保留手写编排版作为稳定基线的前提下，补上 LangChain 工具调度层。**

---

## 三、接入内容

### 1. 新增 LangChain 工具封装文件

新增文件：

```text
app/chain/langchain_tools.py

主要作用：

将现有业务能力封装成 LangChain tools
当前接入的核心工具包括：
analyze_price_data_tool
search_rules_tool
explain_anomaly_tool
build_report_tool

这些工具本质上不是重写业务逻辑，而是复用已经写好的业务函数：

analyze_price_data
search_rules
run_explanation
build_brief_report
2. 新增 LangChain Agent 文件

新增文件：

app/chain/ask_agent.py

主要作用：

构建基于 ChatOllama 的 LangChain agent
为 agent 提供 system prompt 与工具列表
提供 run_langchain_ask() 作为 LangChain 版统一入口执行函数

模型层继续沿用本地 Ollama：

模型：qwen2.5:7b
集成：langchain-ollama

在接入过程中，还额外处理了 Python 客户端访问 Ollama 时的代理环境问题，通过关闭 trust_env 解决了 502 报错问题。

3. 新增 LangChain 路由入口

新增文件：

app/api/routes_ask_langchain.py

新增接口：

POST /ask-lc

这个接口的定位是：

作为 LangChain 正式接入版入口
与手写编排版 /ask 并行存在
便于做效果对比和稳定性评估
4. mixed 场景的特殊处理

在 LangChain 接入过程中发现：

analysis 场景：agent 调用较稳定
retrieval 场景：能调工具，但回答容易基于标题级证据继续扩写
explanation 场景：工具返回结构完整，整体表现较稳
mixed 场景：自由 agent 不稳定，容易出现以下问题：
不调用 build_report_tool
自己擅自改写问题
把“低价样本列表”改成“平台统计”
把“低价规则”改写成“电商价格异常规则”这种过宽问题

因此，mixed 最终采用了受控业务流程：

对 mixed 问题不再完全交给自由 agent 决定流程
在 run_langchain_ask() 中先做任务类型识别
mixed 场景直接强制走 build_report_tool

这样做的目的，是让 LangChain 真正服务业务流程，而不是让业务流程去迁就 agent 的随机性。

四、接入过程中的关键问题与处理
1. LangChain tool 注册失败

问题表现：

使用 @tool 装饰函数时启动报错：
Function must have a docstring if description not provided

原因：

LangChain 在将 Python 函数注册为 tool 时，需要明确的函数说明

处理方式：

为每个 tool 函数补充清晰 docstring
明确工具用途、适用场景和参数说明
2. ChatOllama / Python 客户端调用 Ollama 报 502

问题表现：

原生 ollama run 可用
直接访问 /api/chat 可用
但 ollama.Client(...).chat(...) 和 ChatOllama(...).invoke(...) 报 502

原因：

Python 客户端层读取了环境代理设置，导致本地 127.0.0.1:11434 请求异常

处理方式：

在 Ollama Python 客户端及 ChatOllama 中关闭 trust_env
显式指定本地 base_url

结论：

不是 Ollama 服务本身坏掉
是 Python 客户端环境配置导致的问题
3. LangChain analysis 场景中的“近7天”识别问题

问题表现：

agent 在 tool call 时，把用户问题中的“近7天”改写为“近七天”
原有时间过滤逻辑只识别：
近7天
最近7天
7天内
结果造成时间过滤失效，统计口径从 30 条漂移到 50 条

处理方式：

扩展时间关键词识别，兼容：
近七天
最近七天
七天内
近一周
最近一周

结论：

接入 LangChain 后，必须考虑模型对自然语言表达的等价改写
规则式过滤逻辑不能只写一种表述
4. retrieval 场景回答过度扩写

问题表现：

agent 虽然能正确调用 search_rules_tool
但最终回答容易把标题级证据扩写成不存在的具体规则定义

处理方式：

多轮加强 system prompt
明确要求：
只能基于工具显式字段回答
不允许扩写 section_title / preview_text
证据不足时必须承认不足

结论：

prompt 约束后，retrieval 的 grounded 程度有明显提升
但完全自由的规则回答仍然比手写版更容易漂
5. mixed 场景自由 agent 不稳定

问题表现：

agent 会调用 analyze_price_data_tool 与 search_rules_tool
但经常不调用 build_report_tool
容易自己改写问题与汇报内容

处理方式：

将 mixed 场景改为受控任务路由
在 run_langchain_ask() 中识别 mixed
mixed 场景直接强制走 build_report_tool

结论：

对于高约束业务场景，自由 agent 并不总是最佳方案
“LangChain + 受控流程”比“纯自由 agent”更适合正式项目
五、测试结果
1. analysis（通过）

测试问题：

近7天哪个平台异常低价最多？

结果：

agent 正确调用 analyze_price_data_tool
能返回平台级低价统计
修复“近七天”表达后，统计口径已恢复正确

结论：

LangChain analysis 链路通过
2. retrieval（通过，但回答约束仍需持续控制）

测试问题：

如果标题不完整，规则上该怎么处理？

结果：

agent 正确调用 search_rules_tool
baseline 检索结果可正常返回
回答在加强 prompt 后明显更 grounded
但 retrieval 场景依然是最容易发生标题级扩写的部分

结论：

LangChain retrieval 链路通过
当前仍建议在正式系统中保留更强的回答约束
3. explanation（通过，且表现较稳）

测试问题：

为什么这个商品会被判成高风险？

结果：

agent 正确调用 explain_anomaly_tool
工具返回结构化解释结果：
facts
rule_search
fact_explanation
rule_summary
review_suggestion
final_explanation
最终回答整体较贴工具结果，稳定性优于 retrieval

结论：

LangChain explanation 链路通过
当前是 LangChain 版中表现最稳的一条链路
4. mixed（通过，采用受控流程）

测试问题：

先找出低价商品，再按规则给我写一段简短汇报。

结果：

自由 agent 版本不稳定，容易错误改写问题并跳过 build_report_tool
改为受控任务路由后，mixed 场景直接强制走 build_report_tool
最终输出恢复为：
低价样本结论
规则依据
复核建议

结论：

LangChain mixed 链路通过
但通过方式不是“纯自由 agent”，而是“LangChain + 受控汇报流程”
六、当前总结

LangChain 接入完成后，项目形成了两条并行能力：

1. 手写编排版 /ask

特点：

稳定
路由清晰
输出结构统一
更适合验收与结果可控场景
2. LangChain 版 /ask-lc

特点：

正式接入 LangChain tools 与 agent
可以真实展示工具调用链
更适合体现“模型调工具”的能力
在 analysis / explanation 场景下效果较好
在 retrieval / mixed 场景下，需要更强业务约束
七、当前阶段结论

第四周 LangChain 接入最终没有推翻手写版 /ask，而是形成了如下格局：

手写版 /ask：作为稳定基线
LangChain 版 /ask-lc：作为正式工具编排增强版

一句话总结：

第四周先完成了手写编排版统一入口验收，再补上 LangChain 正式接入；其中 mixed 场景最终采用“LangChain + 受控业务流程”的方案，而不是完全依赖自由 agent。

八、后续优化方向
进一步统一 /ask 与 /ask-lc 的返回结构
为 retrieval 场景增加更强的 grounded answer 约束
继续比较 baseline / FAISS 在 LangChain 场景下的表现差异
在第五周前端中加入 /ask-lc 的可视化展示
后续可考虑将 LangChain 与 LangGraph 进一步结合，用于更正式的工作流节点化编排