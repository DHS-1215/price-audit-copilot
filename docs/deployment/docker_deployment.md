# Docker 部署说明

## 一、文档目的

本文档用于说明 `price-audit-copilot` 项目的 Docker Compose 启动方式、端口规划、环境变量配置、数据库迁移流程、基础接口验证方式以及常见问题处理。

本项目在 8 号窗口阶段完成了 Docker 化收口，目标不是：

> 本机能跑就行。

而是让项目具备基本的：

- 可复现；
- 可验证；
- 可交付；

部署能力。

---

## 二、Docker 运行前提

运行前请确保本机已安装并启动：

- Docker Desktop
- Docker Compose
- Windows 下建议启用 WSL2 后端
- 如需测试 `/ask` 或 `/ask-lc` 模型能力，本机还需要启动 Ollama 服务

本项目默认使用：

- Python 3.11
- FastAPI
- MySQL 8.0
- SQLAlchemy 2.x
- Alembic
- Ollama 本地模型服务

---

## 三、项目相关文件

Docker 相关核心文件位于项目根目录：

```text
Dockerfile
docker-compose.yml
.dockerignore
.env.example
```

---

### 3.1 文件说明

| 文件 | 作用 |
|---|---|
| `Dockerfile` | 构建 FastAPI 应用镜像 |
| `docker-compose.yml` | 同时启动 MySQL 与 API 服务 |
| `.dockerignore` | 排除虚拟环境、缓存、日志、本地 `.env` 等不应进入镜像的文件 |
| `.env.example` | 提供本地运行环境变量示例 |

---

### 3.2 注意事项

```text
.env 不应提交到 GitHub
.env.example 应提交到 GitHub
```

---

## 四、端口说明

当前 Docker Compose 端口规划如下：

| 服务 | 容器端口 | 宿主机端口 | 说明 |
|---|---:|---:|---|
| FastAPI API | 8000 | 8000 | 对外访问 API 与 Swagger |
| MySQL | 3306 | 3307 | 避免与本机 MySQL 3306 冲突 |

也就是说：

```text
浏览器访问 API：     http://127.0.0.1:8000
浏览器访问 Swagger： http://127.0.0.1:8000/docs
宿主机连接 Docker MySQL：127.0.0.1:3307
API 容器连接 MySQL：mysql:3306
```

注意：

- `api` 容器访问 `mysql` 容器时，使用的是 Docker 内部服务名：

```text
mysql:3306
```

- 宿主机访问 Docker MySQL 时，使用的是：

```text
127.0.0.1:3307
```

这两个不要混。

---

## 五、Docker Compose 配置说明

`docker-compose.yml` 中包含两个服务：

```text
mysql
api
```

---

## 5.1 MySQL 服务

MySQL 服务负责提供项目数据库。

核心配置：

```yaml
MYSQL_ROOT_PASSWORD: "123456"
MYSQL_DATABASE: "price_audit_db"
```

字符集配置：

```text
--character-set-server=utf8mb4
--collation-server=utf8mb4_unicode_ci
```

这保证以下中文内容可以正常存储：

- 中文字段；
- 中文备注；
- 中文导出内容。

---

## 5.2 API 服务

API 服务负责启动 FastAPI 应用。

启动命令：

```bash
alembic upgrade head &&
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

也就是说，容器启动时会先执行数据库迁移，再启动 API 服务。

核心数据库连接：

```text
DATABASE_URL=mysql+pymysql://root:123456@mysql:3306/price_audit_db?charset=utf8mb4
```

核心 Ollama 连接：

```text
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

说明：

> `host.docker.internal` 表示容器访问宿主机。

如果 Ollama 在 Windows 本机启动，容器内访问它时应使用这个地址。

---

## 六、启动流程

---

### 6.1 检查 Compose 配置

```bash
docker compose config
```

该命令只检查配置，不启动容器。

如果没有报错，说明 `docker-compose.yml` 语法和结构正常。

---

### 6.2 构建镜像

```bash
docker compose build
```

构建成功后，应看到类似结果：

```text
Image price-audit-copilot-api Built
```

---

### 6.3 启动服务

```bash
docker compose up -d
```

启动成功后，查看容器状态：

```bash
docker compose ps
```

理想状态：

```text
price-audit-mysql   Up / healthy
price-audit-api     Up
```

---

## 七、Alembic 自动迁移说明

API 容器启动时会自动执行：

```bash
alembic upgrade head
```

当前已验证迁移可以从空库自动执行至最新版本：

```text
0001 -> 0002 -> 0003 -> 0004 -> 0005 -> 0006 -> 0007 -> 0008
```

日志中应能看到类似内容：

```text
INFO  [alembic.runtime.migration] Running upgrade 0007 -> 0008
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

这说明：

- MySQL 连接正常；
- Alembic 迁移正常；
- FastAPI 应用启动正常。

---

## 八、基础接口验证

---

### 8.1 验证根接口

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

---

### 8.2 验证 Swagger

浏览器访问：

```text
http://127.0.0.1:8000/docs
```

如果能看到 FastAPI Swagger 页面，说明 API 服务已对外可访问。

---

### 8.3 验证 OpenAPI

```bash
curl.exe http://127.0.0.1:8000/openapi.json
```

预期返回 OpenAPI JSON。

---

### 8.4 验证 Review API 空库响应

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

这说明：

- Review API 路由正常；
- 统一响应外壳正常；
- `trace_id` 正常；
- 空数据库下接口不会报错。

---

## 九、查看日志

查看 API 日志：

```bash
docker compose logs --tail=100 api
```

持续跟踪 API 日志：

```bash
docker compose logs -f api
```

查看 MySQL 日志：

```bash
docker compose logs --tail=100 mysql
```

---

## 十、停止与清理

---

### 10.1 停止容器

```bash
docker compose down
```

---

### 10.2 停止并删除 MySQL 数据卷

如果需要彻底清空 Docker MySQL 数据：

```bash
docker compose down -v
```

注意：

> `docker compose down -v` 会删除 `mysql_data` 数据卷。

删除后数据库会回到空库状态，下一次 `up` 时会重新执行 Alembic 迁移。

---

## 十一、空库说明

当前 Docker Compose 启动的是一个新的 MySQL 数据库。

容器首次启动后，Alembic 会自动创建表结构，并执行已有迁移和规则种子迁移。

但是空库中默认不一定包含以下业务演示数据：

```text
product_raw
product_clean
audit_result
rule_hit
SPEC_RISK 正向样本
audit_result_id=259
```

因此，以下依赖完整业务数据的 smoke test 不建议直接在 Docker 空库中运行：

```bash
python -m scripts.smoke_test_window5_rag_explanation
python -m scripts.smoke_test_window6_ask_orchestration
python -m scripts.smoke_test_window7_review_flow
```

如果需要在 Docker 环境中完整演示 5 / 6 / 7 号窗口链路，需要先执行数据初始化或迁移脚本。

当前 Docker 基础验收重点是：

- 容器可构建；
- 服务可启动；
- 数据库可迁移；
- API 可访问；
- 基础接口可验证。

---

## 十二、常见问题

---

### 12.1 MySQL 3306 端口冲突

如果启动时报错：

```text
listen tcp 0.0.0.0:3306: bind: Only one usage of each socket address is normally permitted
```

原因通常是本机已经有 MySQL 占用了 3306。

解决方式：

```yaml
ports:
  - "3307:3306"
```

此时：

```text
宿主机访问 Docker MySQL：127.0.0.1:3307
api 容器访问 mysql：mysql:3306
```

不要把 API 容器里的 `DATABASE_URL` 改成：

```text
mysql:3307
```

---

### 12.2 API 容器反复重启

查看日志：

```bash
docker compose logs --tail=100 api
```

重点检查：

- `DATABASE_URL` 是否正确；
- `alembic upgrade head` 是否失败；
- `app.api.main:app` 是否能导入；
- 依赖是否安装完整。

---

### 12.3 MySQL 一直不是 healthy

查看 MySQL 日志：

```bash
docker compose logs --tail=100 mysql
```

也可以重启：

```bash
docker compose down
docker compose up -d
```

如果想清空数据库重新来：

```bash
docker compose down -v
docker compose up -d
```

---

### 12.4 Ollama 连接失败

如果 `/ask` 或 `/ask-lc` 调用模型时报错，需要确认宿主机 Ollama 已启动。

宿主机验证：

```bash
curl.exe http://127.0.0.1:11434/api/tags
```

Docker 容器中访问宿主机 Ollama，应使用：

```text
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

### 12.5 接口返回数据为空

如果 Review 列表返回：

```json
{
  "total": 0,
  "items": []
}
```

这不是错误。

原因是 Docker MySQL 是新库，当前只有表结构和部分规则种子数据，没有完整业务演示数据。

需要补充数据初始化后，才能演示完整业务链路。

---

## 十三、当前 Docker 验收结果

当前 8 号窗口已完成 Docker 基础交付验收。

已验证结果：

```text
docker compose config：通过
docker compose build：通过
docker compose up -d：通过
```

容器状态：

```text
price-audit-mysql：healthy
price-audit-api：Up
```

Alembic 自动迁移：

```text
0001 -> 0008 通过
```

接口验证结果：

```text
GET /：200，统一响应外壳正常，trace_id 非空
GET /docs：200
GET /openapi.json：200
GET /api/v1/reviews/tasks：200，空库返回 total=0/items=[]
```

当前端口：

```text
API：http://127.0.0.1:8000
Swagger：http://127.0.0.1:8000/docs
Docker MySQL：127.0.0.1:3307
```

---

## 十四、本阶段结论

Docker 基础部署链路已打通。

当前项目已经从：

```text
本机代码能跑
```

升级为：

```text
可构建镜像
可通过 docker-compose 启动
可自动迁移数据库
可访问 API 文档
可验证基础接口
具备基本交付说明
```

后续如需完整演示 5 / 6 / 7 号窗口业务链路，应继续补充 Docker 环境下的演示数据初始化脚本。