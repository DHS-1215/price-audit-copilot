# Price Audit Copilot / 电商价格异常审核 Copilot

一个面向电商价格审核场景的 AI 辅助分析系统。  
项目基于 **FastAPI + Ollama + Pandas + SQLite + RAG + Streamlit** 构建，不是泛泛的“聊天机器人”，而是围绕真实业务链路设计的 **价格异常审核 Copilot**：支持商品信息结构化抽取、价格异常识别、规则检索解释、自然语言查数、简短汇报生成，以及人工复核建议输出。

---

## 1. 项目背景

在电商价格审核场景里，业务人员每天会面对大量商品数据，常见痛点包括：

- 商品标题和详情文本不规范，字段脏乱
- 同品牌同规格商品在不同平台存在明显价差
- 部分商品价格异常偏低，但需要结合规则口径解释
- 业务人员不仅想知道“有没有异常”，还想知道“为什么判成异常”
- 单纯 SQL 或脚本虽然能算结果，但很难把结果、规则依据、汇报输出和人工复核串成一条链

因此，这个项目的目标不是做一个“会聊天”的 demo，而是做一个更像真实业务系统的 AI Copilot。

---

## 2. 项目目标

本项目围绕“电商价格异常审核”设计，核心目标包括：

1. 对商品标题 / 详情进行结构化抽取
2. 对商品数据进行清洗、规格归一与异常规则判定
3. 基于规则知识库做检索解释
4. 支持自然语言驱动的数据分析与问答
5. 输出适合业务阅读的简短汇报
6. 预留人工复核入口，形成可解释、可追踪的业务闭环

---

## 3. 这不是一个普通聊天机器人

这个项目不是通用问答 demo，而是一个面向真实业务场景的 AI 辅助分析系统。它要解决的问题不是“模型会不会聊天”，而是：

- 数据脏
- 规则多
- 流程长
- 结论必须可解释
- 最终结果要支持人工复核

它的核心不是让模型自由发挥，而是把 **结果层、规则层、汇报层、日志层和人工复核口子** 组织成一条业务闭环。

---

## 4. 当前系统能力概览

### 4.1 统一问答入口

- `POST /ask`
- `POST /ask-lc`
- `POST /extract`

### 4.2 商品结构化抽取

- 品牌抽取
- 规格抽取
- 平台识别
- 价格识别
- 基础结构化 JSON 输出

### 4.3 数据清洗与归一

- 商品标题清洗
- 规格字段基础清洗
- 价格字段清洗与数值化
- 平台字段归并
- 日期字段标准化
- 品牌别名统一
- 规格写法统一
- 标题与规格不一致风险标记

### 4.4 价格异常分析

- 疑似异常低价识别
- 跨平台价差异常识别
- 规格识别风险识别
- 异常原因生成
- 异常明细输出

### 4.5 规则检索与解释

- baseline 规则检索
- embedding + FAISS 向量检索
- 规则证据片段输出
- 结果层 + 规则层联合解释
- 复核建议输出

### 4.6 混合问题处理

- 数据分析类问题
- 规则检索类问题
- 异常解释类问题
- mixed 多步问题
- 简短业务汇报生成

### 4.7 前端与留痕

- Streamlit 页面演示
- JSONL 问答日志落盘
- trace 展示
- 最近问答记录预览
- human review 节点预留

---

## 5. 技术栈

### 已实现

- Python
- FastAPI
- Ollama
- Pydantic
- Requests
- Pandas
- SQLite
- Git / GitHub
- Markdown 规则知识库
- baseline 检索
- Embedding + FAISS
- LangChain
- langchain-ollama
- Streamlit

### 第六周补充

- Dockerfile
- 正式评测集
- README 最终收口
- 简历项目描述与面试讲稿

---

## 6. 系统架构

### 6.1 总体架构

```text
商品数据 / 规则文档
        │
        ▼
数据清洗与归一
(cleaner / normalizer)
        │
        ▼
异常分析
(analysis_tools)
        │
        ├──────────────► 结构化结果 / SQLite / 异常明细
        │
        ▼
规则文档导入与切分
(ingest / chunk / metadata)
        │
        ▼
规则检索
(baseline / FAISS)
        │
        ▼
统一问答入口
(/ask 主线, /ask-lc 展示副线)
        │
        ▼
路由与受控流程
analysis / retrieval / explanation / mixed
        │
        ▼
汇报生成 + trace + 日志落盘
        │
        ▼
Streamlit 页面展示 + human review 口子
```

### 6.2 mixed 场景为什么采用受控流程

mixed 问题不是简单问答，而是一个更高约束的业务过程：

1. 先查数据事实
2. 再检索规则依据
3. 最后组织成适合业务阅读的结论

所以本项目没有把 mixed 全部交给自由 agent 猜工具链，而是采用更稳的受控流程：

**分析 → 检索 → 汇报**

这样做的好处是：

- 可控
- 可解释
- 更符合真实业务顺序
- 更适合在面试里讲系统设计

---

## 7. 当前项目结构

```text
price-audit-copilot/
├── app/
│   ├── api/
│   │   ├── main.py
│   │   ├── routes_ask.py
│   │   └── routes_ask_langchain.py
│   ├── chain/
│   │   ├── ask_agent.py
│   │   └── langchain_tools.py
│   ├── core/
│   ├── data/
│   │   ├── cleaner.py
│   │   ├── normalizer.py
│   │   └── db.py
│   ├── rag/
│   │   ├── ingest.py
│   │   ├── retriever.py
│   │   ├── faiss_store.py
│   │   └── faiss_retriever.py
│   ├── tools/
│   │   ├── analysis_tools.py
│   │   ├── retrieval_tools.py
│   │   ├── explanation_tools.py
│   │   ├── report_tools.py
│   │   └── log_tools.py
│   ├── ui/
│   │   └── streamlit_app.py
│   └── graph/
│       └── workflow.py
├── data/
│   ├── rules/
│   ├── rag/
│   ├── eval/
│   ├── outputs/
│   └── price_audit.db
├── requirements.txt
├── README.md
└── Dockerfile
```

---

## 8. 核心接口说明

### 8.1 `/extract`

用于商品标题 / 详情的结构化抽取。

**输入示例：**

```json
{
  "title": "鸿茅药酒 500ml*4 礼盒装 京东自营 799元"
}
```

**输出示例：**

```json
{
  "brand": "鸿茅",
  "product_name": "药酒",
  "spec": "500ml*4",
  "price": 799,
  "currency": "CNY",
  "promo_text": "礼盒装 京东自营",
  "confidence": 0.8
}
```

### 8.2 `/ask`

当前更稳定的统一问答主入口。

支持路由：

- `analysis`
- `retrieval`
- `explanation`
- `mixed`
- `unknown`

当前统一返回结构包含：

- `route`
- `answer`
- `tools_used`
- `analysis_result`
- `retrieval_result`
- `explanation_result`
- `trace`

**说明：**  
`/ask` 是当前更稳定、更适合正式演示和评测的主链路。

### 8.3 `/ask-lc`

LangChain 展示副线，用于展示：

- ChatOllama 接入
- tool calling 思路
- LangChain 工具封装能力

**说明：**  
`/ask-lc` 的价值在于展示 LangChain 接入能力，而不是接管主前端协议。

---

## 9. 关键模块说明

### `app/data/cleaner.py`

负责原始商品数据清洗，包括价格、平台、标题、时间等字段处理。  
输出文件：`data/cleaned_products_preview.csv`

### `app/data/normalizer.py`

负责品牌与规格归一，尽量把不同表达收敛到统一业务口径。  
输出文件：`data/normalized_products_preview.csv`

### `app/tools/analysis_tools.py`

负责价格异常分析，包括：

- 疑似异常低价识别
- 跨平台价差过大识别
- 规格识别风险识别
- 异常原因生成

输出文件：`data/异常明细.csv`

### `app/data/db.py`

负责轻量数据库落库。  
当前使用 SQLite 对清洗结果、标准化结果和异常分析结果进行存储。  
数据库文件：`data/price_audit.db`

### `app/rag/ingest.py`

负责规则文档导入、切分、metadata 附加和索引准备。  
当前输出：

- `data/rag/rule_chunks.jsonl`
- `data/rag/rule_manifest.json`

### `app/rag/retriever.py`

第三周 baseline 规则检索器。  
当前逻辑包含：

- 业务路由
- 关键词匹配
- 可解释打分

### `app/rag/faiss_store.py / app/rag/faiss_retriever.py`

向量检索实现。  
当前采用：

- Ollama embedding 模型：`qwen3-embedding`
- 本地向量索引：FAISS

### `app/tools/retrieval_tools.py`

把底层检索结果整理成统一的系统可消费格式，输出适合前端、解释链、日志和汇报共同使用的 evidence 结构。

### `app/tools/explanation_tools.py`

基于第二周结果层与第三周规则层生成完整解释。  
核心原则：

**先尊重结果层，再补规则层依据。**

### `app/tools/report_tools.py`

不直接查数据、不直接检索规则，而是把 analysis / retrieval / explanation 的结果整理成更适合业务阅读的简短汇报。

### `app/tools/log_tools.py`

负责日志落盘与序列化，当前将 `/ask` 结果追加写入：

- `data/outputs/ask_logs.jsonl`

### `app/ui/streamlit_app.py`

项目演示页面。  
支持模式切换、参数选择、证据展示、trace 展示、日志预览和 mixed 汇报生成。

### `app/graph/workflow.py`

轻量 workflow 骨架，体现：

- `route_query_node`
- `run_analysis_node`
- `run_retrieval_node`
- `run_explanation_node`
- `compose_answer_node`
- `human_review_node`

---

## 10. 前端演示能力

当前 Streamlit 页面已支持：

- 输入自然语言问题
- 调用 `/ask` 主链路
- 调用 `/ask-lc` LangChain 展示链路
- 切换 baseline / faiss 检索模式
- 设置 `top_k`
- 控制是否返回 `trace`

页面当前可展示内容包括：

- 最终回答
- 问题路由类型
- 调用工具列表
- 数据分析结果区
- 规则证据片段区
- 异常解释区
- 工具调用链路区
- 原始 JSON 调试区
- 最近问答日志预览
- 一键生成 mixed 简短汇报

---

## 11. 规则知识库

当前规则文档位于 `data/rules/`，已包括：

- `platform_price_rules.md`
- `spec_normalization_rules.md`
- `low_price_detection_rules.md`
- `cross_platform_gap_rules.md`
- `manual_review_process.md`
- `faq.md`

当前 ingest 结果：

- 规则文档数量：6
- chunk 数量：43

---

## 12. 示例问题

### 12.1 数据分析类

- 哪些商品是疑似异常低价？
- 哪些商品规格识别有风险？
- 哪个平台低价最多？
- 哪个品牌跨平台价差最大？
- 近 7 天哪个平台异常低价最多？

### 12.2 规则检索类

- 如果标题不完整，规则上该怎么处理？
- 低价异常规则是怎么定义的？
- 跨平台价差异常是怎么判的？
- 人工复核时应该先看什么？

### 12.3 异常解释类

- 为什么这个商品会被判成高风险？
- 为什么这个商品会被判成疑似异常低价？

### 12.4 多步问题类

- 先找出低价商品，再按规则给我写一段简短汇报。
- 哪个平台异常低价最多？再解释判断依据。
- 先看最近异常清单，再总结需要人工复核的重点。

---

## 13. 设计取舍

### 13.1 为什么第三周先做 baseline，再补向量检索

第三周没有一开始就直接上向量检索，而是先做了一版 baseline retriever。原因是：

- 先验证规则文档内容是否合理
- 先验证 chunk 切分是否合理
- 先验证 FAQ 和主规则文档能否支撑解释链
- 先把“结果层 → 规则层 → 复核建议”这条链跑通

因此第三周最终形成的是：

- baseline 检索
- 向量检索
- 解释链

而不是只做单一检索方案。

### 13.2 为什么 `/ask` 和 `/ask-lc` 并行存在

第四周没有直接把所有问题都交给 LangChain 自由 agent，而是先完成一版手写编排版统一 ask 入口。原因是：

- 先保证业务主链稳定
- 先让 analysis / retrieval / explanation / mixed 四类问题跑通
- 先建立统一输出结构
- 先建立日志与验收体系

因此两条链的定位分别是：

- `/ask`：更稳，更适合正式演示与验收
- `/ask-lc`：更适合展示 tool calling 与 LangChain 接入能力

### 13.3 为什么 mixed 必须继续走受控流程

mixed 问题通常具有更强的业务顺序约束，例如：

1. 先看事实结果
2. 再找规则依据
3. 最后组织汇报

这种场景如果全部交给自由 agent，容易出现流程漂移、问题改写或证据错配。  
因此 mixed 当前继续采用受控流程，而不是完全依赖自由 agent 决定步骤。

---

## 14. 评测结果

本项目在第六周补充了正式评测集，共设计 30 条评测用例，分为三类：

- 数据分析类：10 条
- 规则解释类：10 条
- 多步问题类：10 条

每条评测记录统一保留以下信息：

1. 问题
2. 预期答案 / 核心要点
3. 实际输出
4. 是否通过
5. 错误原因（若失败）

### 评测结论

本轮共完成 30 / 30 条用例评测。

- 通过：9
- 部分通过：11
- 不通过：10

### 当前系统表现

从评测结果看，当前版本已经具备基础可用性：

- `analysis` 链路可完成基础统计、样本列表、平台/品牌维度分析
- `retrieval` 链路能够命中规则文档、FAQ 和处理流程文档
- `mixed` 链路已可完成“数据分析 + 规则检索 + 汇报生成”的基本闭环
- Docker 容器环境下，`/extract`、`/ask`、`/docs` 已完成联调验证

### 主要通过类型

当前系统在以下场景表现较稳定：

- 基础分析类问题  
  例如：统计异常低价数量、找出跨平台价差最大的品牌、汇总低价样本数量等

- 基础规则检索类问题  
  例如：低价规则来源字段、标题不完整处理规则、规格归一相关规则

- 基础多步问题  
  例如：先统计样本，再补规则依据，再输出简短汇报

### 主要问题类型

评测同时暴露出当前版本的几个明显短板：

1. 路由稳定性不足  
   一部分本应进入 `analysis` 的问题被误判为 `unknown`，退回到了通用模型回答；也有部分本应进入 `retrieval` 的规则解释问题，被误打到 `analysis` 总览。

2. 条件筛选能力不够稳定  
   对“品牌 + 规格”“平台过滤”“规则来源 = both”“显式阈值命中”等带条件的问题，系统有时不能稳定输出目标子集，而会退化成全局 overview。

3. 检索后的解释深度不足  
   部分 `retrieval` 用例虽然命中了正确文档和章节，但最终 `answer` 停留在“命中了哪个规则文档”的层面，没有真正把规则口径解释清楚。

4. mixed 场景的结果收束不够精准  
   多步链路能够跑通，但在一些问题中，分析结果没有严格对齐用户指定的目标对象，最终回答更像“总览 + 建议”，而不是“精准子集 + 建议”。

---

## 15. 已知限制

当前版本仍存在以下限制：

### 1. 路由规则仍偏启发式

`route_query` 目前主要依赖关键词与问题模式进行判别。对于“问得较泛”的问题，或者“同时包含分析词和规则词”的问题，路由结果还不够稳定，容易出现：

- 本应走 `analysis` 却退到 `unknown`
- 本应走 `retrieval` 却误打到 `analysis`
- 本应做条件筛选却退化成 overview

### 2. 条件过滤问题支持还不够稳

对于以下类型问题，当前系统有时不能稳定命中目标子集：

- 品牌 + 规格联合过滤
- 平台过滤
- `low_price_rule_source = both`
- 显式阈值命中样本
- 先限定条件再生成建议的多步问题

这说明分析工具层对“自然语言条件 → 结构化过滤条件”的映射还不够强。

### 3. 检索命中 ≠ 解释充分

当前 `retrieval` 链路多数情况下能够命中文档，但部分回答只说明了“最相关证据来自哪个章节”，并没有进一步把规则口径讲透。  
也就是说，检索结果可用，但解释层仍有提升空间。

### 4. mixed 场景的输出组织还可优化

当前 mixed 链路已经能完成“分析 + 检索 + 汇报”的基础闭环，但在部分问题中，最终 answer 更偏向通用业务总结，而不是严格按照用户指定顺序进行组织。例如：

- 本应先列出目标样本，再补规则依据
- 实际却变成先给 overview，再给复核建议

### 5. 容器化部署仍依赖宿主机 Ollama

当前 Docker 容器内的 FastAPI 服务已通过环境变量方式访问宿主机 Ollama，因此系统已具备基础容器化能力。  
但目前仍不是“模型与服务完全一体化封装”的独立部署形态，运行时需要保证宿主机 Ollama 可访问。

### 6. 当前评测仍以规则与样例数据为主

本轮评测基于当前样例商品数据、规则文档和 FAQ 构建，适合验证项目主链路与工程结构。  
但其覆盖面仍有限，尚未扩展到：

- 更多品牌与规格写法
- 更复杂的促销口径
- 更大规模样本数据
- 更复杂的对话上下文场景

---

## 16. 后续优化方向

下一步准备从以下几个方向继续优化：

1. 强化路由器  
   提升 `analysis / retrieval / mixed / unknown` 的判别稳定性，减少误路由和通用回答兜底次数。

2. 增强条件解析能力  
   将品牌、规格、平台、规则来源、阈值类型等自然语言条件，更稳定地映射为分析工具可执行的过滤参数。

3. 优化检索后的解释层  
   不只返回“命中哪个文档”，而是进一步把规则口径讲清楚，提升回答的解释力。

4. 增加评测自动化  
   后续可补充 `eval_cases.json + run_eval.py` 的半自动执行能力，将 route、tools_used、是否命中预期字段等指标自动记录下来。

5. 完善独立部署形态  
   后续可继续探索将本地模型服务、应用服务、规则索引构建流程进行更完整的容器化封装。

---

## 17. 本地运行方式

### 17.1 安装依赖

```bash
pip install -r requirements.txt
```

### 17.2 启动 FastAPI

```bash
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001
```

### 17.3 启动 Streamlit

```bash
streamlit run app/ui/streamlit_app.py
```

### 17.4 启动 Ollama

```bash
ollama serve
ollama pull qwen2.5:7b
```

---

## 18. Docker 启动方式

### 18.1 构建镜像

```bash
docker build -t price-audit-copilot .
```

### 18.2 启动容器

```bash
docker run -p 8001:8001 -e OLLAMA_BASE_URL=http://host.docker.internal:11434 price-audit-copilot
```

**说明：**

- 当前 Docker 版本已验证 `/docs`、`/extract`、`/ask` 主链路可运行
- 容器内 FastAPI 服务通过 `OLLAMA_BASE_URL` 访问宿主机 Ollama
- 当前目标是证明项目具备最小可交付能力，而不是追求生产级部署复杂度

---

## 19. 周次推进脉络

### 第 1 周

- FastAPI 后端骨架
- Ollama 接入
- `/ask` 与 `/extract` 跑通
- Swagger 页面可直接调接口
- 准备样例商品数据集

### 第 2 周

- 数据清洗
- 品牌 / 规格归一
- 异常分析
- SQLite 落库
- 输出异常明细

### 第 3 周

- 规则知识库
- FAQ
- ingest / chunk / metadata
- baseline 检索
- FAISS 向量检索
- 解释链

### 第 4 周

- 统一 `/ask` 入口
- `report_tools`
- 日志落盘
- baseline / FAISS 双模式接入统一入口
- LangChain 正式接入
- `/ask-lc`

### 第 5 周

- Streamlit 页面
- mixed 简短汇报按钮
- 最近问答日志预览
- 轻量 workflow 骨架

### 第 6 周

- README 最终收口
- Dockerfile
- 正式评测集
- 简历描述与面试讲稿

---

## 21. 这个系统比普通 SQL / 脚本强在哪

单纯 SQL 或脚本可以算结果，但很难同时做到：

- 自然语言驱动问答
- 规则依据检索与展示
- 解释型回答
- 简短业务汇报生成
- trace 留痕
- human review 口子
- 前端演示与统一 API

本项目的价值不在于“替代 SQL”，而在于把 **数据事实、规则依据、结论表达和人工复核** 串成一个更完整的业务闭环。