# 鸿茅药酒电商维价审核 Copilot（企业级升级版）

## 一、项目定位

本项目是一个面向企业内部电商维价业务的 AI 审核辅助系统原型。

它不是通用聊天机器人，也不是简单的 RAG 问答 Demo，而是围绕电商维价审核场景，构建了一套从商品数据清洗、异常判定、规则解释、统一问答编排、人工复核闭环到日志审计与
Docker 部署交付的完整业务链路。

项目核心目标：

```text
帮助业务人员更快发现价格异常
帮助业务人员理解异常依据
帮助业务人员完成复核动作并留痕
帮助系统具备可测试、可部署、可交付能力
```

---

## 二、业务背景

在电商维价场景中，业务人员需要持续关注多个平台上的商品价格、规格、标题、店铺等信息。

典型问题包括：

- 商品是否低于维价规则要求；
- 不同平台之间是否存在明显价差；
- 商品标题和规格字段是否存在不一致；
- 某条异常为什么被系统判定为异常；
- 业务人员复核后如何留痕；
- 后续如何导出结果并追踪处理过程。

本项目以鸿茅药酒相关电商商品数据为业务对象，构建了一个 AI 辅助审核系统，用于模拟企业内部价格巡检、异常识别、规则解释与人工复核流程。

---

## 三、核心能力

当前项目已覆盖以下核心能力：

- 商品数据清洗与标准化；
- 异常规则判定；
- 规则命中留痕；
- RAG 规则检索；
- 规则解释与 citation 输出；
- 统一 `/ask` 问答编排；
- LangChain `/ask-lc` 增强链；
- 人工复核任务流；
- 复核状态机；
- 复核记录留痕；
- 中文字段存储与导出；
- pytest 正式测试；
- smoke test 烟雾测试；
- Docker Compose 部署。

---

## 四、系统主链路

系统主链路如下：

```text
原始商品数据
  ↓
清洗与标准化
  ↓
异常判定
  ↓
规则命中记录
  ↓
RAG 检索规则依据
  ↓
/ask 统一问答编排
  ↓
人工复核任务
  ↓
复核记录留痕
  ↓
结果导出
```

---

### 4.1 数据链路

原始商品数据进入系统后，先进入 `product_raw`，再经过清洗和标准化，形成 `product_clean`。

---

### 4.2 规则链路

系统通过规则引擎生成异常判定结果，并将规则命中事实写入：

```text
audit_result
rule_hit
```

---

### 4.3 RAG 解释链路

规则文档被切分为 `rule_chunk`，通过以下检索方式返回 evidence 和 citation，用于解释异常依据：

- baseline 检索；
- vector 检索；
- hybrid 检索。

---

### 4.4 问答编排链路

用户通过 `/ask` 输入自然语言问题，系统根据问题类型路由到：

```text
analysis
retrieval
explanation
mixed
```

不同类型问题走不同工具链，避免所有问题都交给自由 Agent 乱跑。

---

### 4.5 人工复核链路

异常结果可以创建为复核任务，业务人员可以：

- 查看异常；
- 查看规则依据；
- 添加备注；
- 确认异常；
- 标记误报；
- 忽略任务；
- 关闭任务；
- 查询复核记录；
- 导出复核结果。

---

## 五、技术栈

---

### 5.1 后端与接口

- Python 3.11
- FastAPI
- Uvicorn
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- MySQL 8.0
- PyMySQL

---

### 5.2 数据处理

- Pandas
- 自定义清洗逻辑
- 自定义规则引擎

---

### 5.3 RAG 与大模型

- Ollama
- LangChain
- FAISS
- ChromaDB
- baseline 检索
- vector 检索
- hybrid 检索
- rerank 预留

---

### 5.4 测试与部署

- pytest
- requests
- Docker
- docker-compose

---

### 5.5 页面与工作台

- Streamlit

---

## 六、项目目录结构

当前核心目录结构：

```text
price-audit-copilot/
│
├── app/
│   ├── api/                  # FastAPI 接口入口
│   ├── core/                 # 配置、日志、异常、响应、trace
│   ├── db/                   # 数据库 session
│   ├── llm/                  # Ollama 客户端
│   ├── models/               # SQLAlchemy ORM 模型
│   ├── orchestrators/        # /ask 编排层
│   ├── rag/                  # RAG 检索、解释、向量检索
│   ├── repositories/         # 仓储层
│   ├── schemas/              # Pydantic schema
│   ├── services/             # 业务服务层
│   ├── tools/                # LangChain / 工具函数
│   └── workflows/            # 工作流预留
│
├── app_ui/                   # Streamlit 页面
│
├── alembic/                  # 数据库迁移
│   └── versions/
│
├── data/                     # 样例数据、规则文档、RAG 数据
│   ├── rules/
│   ├── rag/
│   ├── faiss/
│   ├── processed/
│   └── samples/
│
├── docs/                     # 项目文档
│   ├── database/
│   ├── deployment/
│   ├── handoff/
│   ├── source_of_truth/
│   └── testing/
│
├── scripts/                  # 构建、迁移、smoke test 脚本
│
├── tests/                    # pytest 正式测试
│   ├── regression/
│   └── review/
│
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
├── requirements.txt
└── README.md
```

---

## 七、快速启动：本地开发环境

---

### 7.1 创建并激活环境

```bash
conda create -n lc_v1 python=3.11
conda activate lc_v1
```

---

### 7.2 安装依赖

```bash
pip install -r requirements.txt
```

---

### 7.3 准备环境变量

复制 `.env.example` 为 `.env`：

```bash
copy .env.example .env
```

本地 MySQL 示例：

```text
DATABASE_URL=mysql+pymysql://root:123456@127.0.0.1:3306/price_audit_db?charset=utf8mb4
```

---

### 7.4 执行数据库迁移

```bash
alembic upgrade head
```

---

### 7.5 启动 FastAPI

```bash
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

---

### 7.6 访问接口文档

```text
http://127.0.0.1:8000/docs
```

---

## 八、Docker 部署

本项目已支持 Docker Compose 启动。

---

### 8.1 检查 Compose 配置

```bash
docker compose config
```

---

### 8.2 构建镜像

```bash
docker compose build
```

当前已验证构建成功：

```text
Image price-audit-copilot-api Built
```

---

### 8.3 启动服务

```bash
docker compose up -d
```

---

### 8.4 查看容器状态

```bash
docker compose ps
```

当前已验证：

```text
price-audit-mysql   Up / healthy
price-audit-api     Up
```

---

### 8.5 端口说明

| 服务      | 容器端口 | 宿主机端口 |
|---------|-----:|------:|
| FastAPI | 8000 |  8000 |
| MySQL   | 3306 |  3307 |

说明：

```text
宿主机访问 Docker MySQL：127.0.0.1:3307
API 容器访问 MySQL：mysql:3306
```

---

### 8.6 基础接口验证

验证根接口：

```bash
curl.exe http://127.0.0.1:8000/
```

预期返回：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "trace_id": "非空字符串",
  "data": {
    "message": "Price Audit Copilot API is running."
  }
}
```

验证 Review API：

```bash
curl.exe "http://127.0.0.1:8000/api/v1/reviews/tasks?page=1&page_size=5"
```

空库下预期返回：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "trace_id": "非空字符串",
  "data": {
    "total": 0,
    "page": 1,
    "page_size": 5,
    "items": []
  }
}
```

---

### 8.7 Docker 说明

Docker Compose 启动时会自动执行：

```bash
alembic upgrade head
```

当前已验证 Alembic 可从空库迁移至最新版本：

```text
0001 -> 0008
```

Docker 新库默认是空业务库，适合验证：

- 镜像构建；
- 容器启动；
- 数据库迁移；
- API 可访问；
- `/docs` 可访问；
- 基础接口可返回。

完整业务 smoke test 依赖已有业务样本，例如：

```text
audit_result_id = 259
```

需要先准备演示数据。

详细说明见：

```text
docs/deployment/docker_deployment.md
```

---

## 九、核心接口

---

### 9.1 健康检查

```http
GET /
```

返回统一响应外壳：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "trace_id": "...",
  "data": {
    "message": "Price Audit Copilot API is running."
  }
}
```

---

### 9.2 统一问答主链

```http
POST /ask
```

用于处理自然语言问题，支持：

```text
analysis
retrieval
explanation
mixed
```

---

### 9.3 LangChain 增强链

```http
POST /ask-lc
```

用于展示 tool calling / LangChain 增强能力，不替代 `/ask` 主链。

---

### 9.4 结构化抽取

```http
POST /extract
```

用于从商品标题中抽取结构化信息。

---

### 9.5 审核执行

```http
POST /audit/run
```

用于触发审核流程。

---

### 9.6 人工复核接口

复核接口统一位于：

```text
/api/v1/reviews
```

核心接口：

```http
POST /api/v1/reviews/tasks
GET  /api/v1/reviews/tasks
GET  /api/v1/reviews/tasks/{task_id}

POST /api/v1/reviews/tasks/{task_id}/confirm
POST /api/v1/reviews/tasks/{task_id}/reject
POST /api/v1/reviews/tasks/{task_id}/ignore
POST /api/v1/reviews/tasks/{task_id}/close
POST /api/v1/reviews/tasks/{task_id}/comment

GET  /api/v1/reviews/records
GET  /api/v1/reviews/export
```

复核接口已统一响应外壳：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "trace_id": "...",
  "data": {}
}
```

---

## 十、测试与验收

---

### 10.1 pytest 正式测试

运行全部正式测试：

```bash
pytest tests -q
```

当前验收结果：

```text
6 passed
```

当前 pytest 覆盖：

- review API 统一响应契约；
- review 状态机；
- review 中文字段；
- 已有 regression 测试。

---

### 10.2 Review 专项测试

```bash
pytest tests\review -q
```

覆盖：

- `success` / `code` / `message` / `trace_id` / `data` 响应契约；
- `pending` / `confirmed` / `closed` 状态流转；
- 中文字段存储与导出。

---

### 10.3 5号窗口 RAG smoke test

```bash
python -m scripts.smoke_test_window5_rag_explanation
```

当前验收结果：

```text
PASS: 9
FAIL: 0
SKIP: 0
```

覆盖：

- baseline 检索；
- vector 检索；
- hybrid 检索；
- `low_price` 解释链；
- `cross_platform_gap` 解释链；
- `spec_risk` 解释链；
- evidence / citation 输出。

---

### 10.4 6号窗口 `/ask` 编排 smoke test

```bash
python -m scripts.smoke_test_window6_ask_orchestration
```

当前验收结果：

```text
PASS: 6
FAIL: 0
```

覆盖：

- `/ask analysis`
- `/ask retrieval`
- `/ask explanation`
- `/ask mixed`
- `/ask-lc mixed`

---

### 10.5 7号窗口人工复核 smoke test

```bash
python -m scripts.smoke_test_window7_review_flow
python -m scripts.smoke_test_window7_review_chinese
python -m scripts.smoke_test_window7_review_state_machine
```

当前验收结果：

```text
review_flow：PASS: 7 / FAIL: 0
review_chinese：通过
review_state_machine：PASS: 6 / FAIL: 0
```

详细说明见：

```text
docs/testing/testing_guide.md
```

---

## 十一、当前验收结果

当前 8 号窗口阶段已完成以下收口：

| 验收项                    | 状态      |
|------------------------|---------|
| review API 统一响应外壳      | 完成      |
| `trace_id` 成功响应接入      | 完成      |
| pytest 正式测试            | 通过      |
| 5号窗口 RAG smoke test    | 通过      |
| 6号窗口 ask 编排 smoke test | 通过      |
| 7号窗口 review smoke test | 通过      |
| Docker build           | 通过      |
| `docker compose up`    | 通过      |
| MySQL 容器               | healthy |
| API 容器                 | running |
| Alembic 自动迁移           | 通过      |
| `/docs`                | 可访问     |
| `/openapi.json`        | 可访问     |

---

## 十二、项目亮点

---

### 12.1 不是通用聊天机器人，而是业务系统

本项目围绕电商维价审核场景展开，AI 能力服务于业务链路，而不是单纯展示模型对话。

---

### 12.2 规则引擎与 RAG 解释分层

异常判定由规则引擎负责。

RAG 解释层只解释已有判定事实，避免模型反向覆盖业务结果。

---

### 12.3 主链与增强链分离

`/ask` 是正式主链，强调：

- 稳定；
- 可控；
- 可验收。

`/ask-lc` 是增强链，用于展示 LangChain tool calling 能力，但不替代主链。

---

### 12.4 人工复核闭环

项目不是只给出“异常结论”，而是支持业务人员继续处理异常：

- 确认异常；
- 标记误报；
- 忽略任务；
- 关闭任务；
- 添加备注；
- 查询记录；
- 导出结果。

---

### 12.5 工程化收口

项目补齐了：

- 统一配置；
- 统一响应；
- 统一异常；
- `trace_id`；
- 日志；
- Alembic 迁移；
- pytest；
- smoke test；
- Docker Compose；
- 部署文档；
- 测试文档。

---

## 十三、面试讲解要点

可以从下面这条主线讲项目：

> 我做的是一个面向电商维价审核场景的 AI 辅助系统。
>
> 它不是普通聊天机器人，而是把商品清洗、异常判定、规则解释、统一问答和人工复核闭环串成了一条完整业务链路。

重点可讲：

- 为什么先做规则判定，再做 RAG 解释；
- 为什么 `/ask` 不完全交给自由 Agent；
- 为什么保留 `/ask` 和 `/ask-lc` 两条链；
- 为什么要做人工复核闭环；
- 为什么要做 `trace_id`、日志、统一响应；
- 为什么最后补 pytest 和 Docker；
- 如何验证这个项目不是“只能自己电脑跑”。

推荐回答方向：

```text
规则引擎负责确定业务事实；
RAG 负责提供可追溯解释依据；
/ask 负责编排不同任务类型；
人工复核负责形成业务闭环；
日志、测试、Docker 负责让项目可验证、可交付。
```

---

## 十四、后续扩展方向

后续可以继续增强：

- Docker 演示数据 seed 脚本；
- 测试数据库隔离；
- CI 自动测试；
- CSV / Excel 导出；
- 更完整的 API 文档；
- 权限与角色控制；
- 多品牌规则配置；
- 规则版本管理页面；
- RAG rerank 正式接入；
- LangGraph 工作流增强；
- 前后端分离工作台。

---

## 十五、当前项目状态

当前项目已经从早期的“能跑原型”升级为：

- 具备正式工程结构；
- 具备数据库迁移；
- 具备规则判定能力；
- 具备 RAG 规则解释能力；
- 具备统一问答编排；
- 具备人工复核闭环；
- 具备测试验证；
- 具备 Docker Compose 部署；
- 具备部署与测试文档。