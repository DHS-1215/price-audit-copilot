# Price Audit Copilot / 电商价格异常审核 Copilot

一个面向**电商价格异常审核场景**的 AI 辅助分析系统。  
项目基于 **FastAPI + Ollama + Pandas + SQLite + RAG + Streamlit + Docker** 构建，不是泛泛的“聊天机器人”，而是围绕真实业务链路设计的 **价格异常审核 Copilot**。

它支持：

- 商品信息结构化抽取
- 数据清洗、规格归一与异常规则判定
- 规则知识库检索与异常解释
- 自然语言查数与问答
- 简短业务汇报生成
- 人工复核建议输出

---

## 项目亮点

- **6 周完成核心链路搭建**：从数据处理、规则判定到 RAG 检索、API、页面演示与 Docker 容器化全部打通
- **3 个统一入口接口**：`/ask`、`/ask-lc`、`/extract`
- **双检索方案**：支持 baseline 规则检索 + embedding + FAISS 向量检索
- **规则知识库可解释**：基于 **6 份规则 / FAQ 文档**，切分为 **43 个规则 chunk**
- **支持多类问答路由**：`analysis`、`retrieval`、`explanation`、`mixed`
- **具备可演示与可交付能力**：包含 Streamlit 页面、JSONL 日志留痕、trace 输出、Docker build + run 验证
- **主链路已验证可运行**：Docker 版本已验证 `/docs`、`/extract`、`/ask`

---

## 1. 项目背景

在电商价格审核场景中，业务人员每天会面对大量商品数据，常见痛点包括：

- 商品标题和详情文本不规范，字段脏乱
- 同品牌同规格商品在不同平台存在明显价差
- 部分商品价格异常偏低，但需要结合规则口径解释
- 业务人员不仅想知道“有没有异常”，还想知道“为什么判成异常”
- 单纯 SQL 或脚本虽然能算结果，但很难把结果、规则依据、汇报输出和人工复核串成一条链

因此，这个项目的目标不是做一个“会聊天”的 demo，  
而是做一个更像真实业务系统的 **AI Copilot**。

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

## 3. 核心能力概览

### 3.1 统一问答入口

- `POST /ask`
- `POST /ask-lc`
- `POST /extract`

### 3.2 商品结构化抽取

支持从商品标题 / 详情中抽取：

- 品牌
- 商品名
- 规格
- 平台
- 价格
- 促销文本
- 基础结构化 JSON 输出

### 3.3 数据清洗与归一

支持：

- 商品标题清洗
- 规格字段基础清洗
- 价格字段数值化
- 平台字段归并
- 日期字段标准化
- 品牌别名统一
- 规格写法统一
- 标题与规格不一致风险标记

### 3.4 价格异常分析

支持：

- 疑似异常低价识别
- 跨平台价差异常识别
- 规格识别风险识别
- 异常原因生成
- 异常明细输出
- SQLite 落库

### 3.5 规则检索与解释

支持：

- baseline 规则检索
- embedding + FAISS 向量检索
- 规则证据片段返回
- 结果层 + 规则层联合解释
- 复核建议输出

### 3.6 混合问题处理

支持：

- 数据分析类问题
- 规则检索类问题
- 异常解释类问题
- `mixed` 多步问题
- 简短业务汇报生成

### 3.7 页面展示与留痕

支持：

- Streamlit 页面演示
- JSONL 问答日志落盘
- trace 展示
- 最近问答记录预览
- human review 节点预留

---

## 4. 技术栈

### 后端与数据处理
- Python
- FastAPI
- Pandas
- SQLite
- Pydantic
- Requests

### 大模型与检索增强
- Ollama
- LangChain
- RAG
- Embedding
- FAISS

### 前端与演示
- Streamlit

### 工程化
- Git / GitHub
- Docker

---

## 5. 系统架构

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

---

## 6. 为什么 mixed 场景采用受控流程

`mixed` 问题不是简单问答，而是一个更高约束的业务过程：

1. 先查数据事实
2. 再检索规则依据
3. 最后组织成适合业务阅读的结论

因此本项目没有把 mixed 全部交给自由 agent 猜工具链，而是采用更稳的受控流程：

**分析 → 检索 → 汇报**

这样做的好处是：

- 可控
- 可解释
- 更符合真实业务顺序
- 更适合面试中讲清系统设计思路

---

## 7. 项目结构

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
├── Dockerfile
└── README.md
```

---

## 8. API 示例

### 8.1 `/extract`

用于商品标题 / 详情的结构化抽取。

**请求示例：**

```json
{
  "title": "鸿茅药酒 500ml*4 礼盒装 京东自营 799元"
}
```

**返回示例：**

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

---

### 8.2 `/ask`

当前更稳定的统一问答主入口。

支持路由：

- `analysis`
- `retrieval`
- `explanation`
- `mixed`
- `unknown`

统一返回结构包含：

- `route`
- `answer`
- `tools_used`
- `analysis_result`
- `retrieval_result`
- `explanation_result`
- `trace`

**问题示例：**

```json
{
  "question": "当前共有多少条疑似异常低价记录？"
}
```

---

### 8.3 `/ask-lc`

LangChain 工具链版本入口，主要用于展示工具编排与扩展能力。  
当前主线以 `/ask` 为主，`/ask-lc` 作为展示副线。

---

## 9. 知识库说明

当前规则知识库包含：

- 低价异常规则
- 规格归一与规格风险规则
- 跨平台价差异常规则
- 人工复核流程
- FAQ 等文档

当前共整理：

- **6 份规则 / FAQ 文档**
- **43 个规则 chunk**

知识库检索支持：

- baseline 检索
- embedding + FAISS 向量检索

---

## 10. 快速开始

### 10.1 本地运行

安装依赖：

```bash
pip install -r requirements.txt
```

启动 FastAPI：

```bash
uvicorn app.api.main:app --reload
```

启动后可访问：

```bash
http://127.0.0.1:8000/docs
```

启动 Streamlit：

```bash
streamlit run app/ui/streamlit_app.py
```

---

### 10.2 Docker 运行

构建镜像：

```bash
docker build -t price-audit-copilot .
```

运行容器：

```bash
docker run --rm -p 8000:8000 ^
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 ^
  price-audit-copilot
```

> Windows PowerShell 可按本机环境调整换行方式。

**说明：**

- 当前 Docker 版本已验证 `/docs`、`/extract`、`/ask` 主链路可运行
- 容器内 FastAPI 服务通过 `OLLAMA_BASE_URL` 访问宿主机 Ollama
- 当前目标是验证最小可交付能力，而不是追求生产级部署复杂度

---

## 11. 项目验收与完成度

当前项目已完成：

- 核心数据处理链路
- 异常规则判定链路
- 规则知识库导入与切分
- baseline / FAISS 双检索
- `/ask`、`/ask-lc`、`/extract` 三类接口
- Streamlit 页面演示
- JSONL 日志留痕与 trace 输出
- Docker build + run 验证
- 正式评测 / 验收样例整理

> 核心版本已在 6 周内完成，后续仍可继续扩展检索效果、工作流编排与部署能力。

---

## 12. 这个系统比普通 SQL / 脚本强在哪

单纯 SQL 或脚本可以算结果，但很难同时做到：

- 自然语言驱动问答
- 规则依据检索与展示
- 解释型回答
- 简短业务汇报生成
- trace 留痕
- human review 口子
- 前端演示与统一 API

本项目的价值不在于“替代 SQL”，  
而在于把 **数据事实、规则依据、结论表达和人工复核** 串成一个更完整的业务闭环。

---

## 13. 后续优化方向

后续可继续扩展的方向包括：

- 丰富规则知识库与 FAQ 覆盖范围
- 优化 embedding 检索质量与 rerank 机制
- 增强 mixed 场景的工作流编排能力
- 完善评测集与自动化测试
- 支持更完整的人工复核流转
- 继续推进部署与工程化能力

---

## 14. 适用岗位方向

这个项目更适合用于展示以下方向的能力：

- AI 应用开发工程师
- 大模型应用开发工程师
- RAG / Agent 应用开发方向
- Python 自动化开发 / 数据智能应用方向
