# 测试说明文档

## 一、文档目的

本文档用于说明 `price-audit-copilot` 项目的测试结构、测试命令、烟雾测试范围、回归测试范围以及当前 8 号窗口阶段的测试验收结果。

本项目测试目标不是追求覆盖所有边角逻辑，而是优先保证：

- 核心业务主链路可验证；
- 关键接口契约稳定；
- 人工复核闭环不被破坏。

---

## 二、当前测试分类

当前项目测试分为两类：

```text
pytest 正式测试
scripts smoke test 烟雾测试
```

---

### 2.1 pytest 正式测试

位置：

```text
tests/
```

作用：

> 纳入正式回归测试，适合后续持续执行。

当前主要覆盖：

- review API 统一响应契约；
- review 状态机；
- review 中文字段；
- 已有 regression 测试。

---

### 2.2 smoke test 烟雾测试

位置：

```text
scripts/
```

作用：

> 用于快速验证各窗口关键链路是否仍然可跑。

当前主要覆盖：

- 5号窗口 RAG 检索与规则解释链；
- 6号窗口 `/ask` 主链与 `/ask-lc` 增强链；
- 7号窗口人工复核闭环；
- 7号窗口中文字段；
- 7号窗口复核状态机。

---

## 三、pytest 测试结构

当前新增 review 测试目录：

```text
tests/review/
  __init__.py
  test_review_response_contract.py
  test_review_state_machine.py
  test_review_chinese_fields.py
```

---

### 3.1 review response contract 测试

文件：

```text
tests/review/test_review_response_contract.py
```

验证目标：

- review API 成功响应必须统一使用 `ApiResponse` 外壳；
- `success` / `code` / `message` / `trace_id` / `data` 字段必须存在；
- `trace_id` 不能为空；
- `data` 内仍保留原业务字段。

重点验证接口：

```http
POST /api/v1/reviews/tasks
GET  /api/v1/reviews/tasks
GET  /api/v1/reviews/records
GET  /api/v1/reviews/export
```

---

### 3.2 review state machine 测试

文件：

```text
tests/review/test_review_state_machine.py
```

验证目标：

- `pending` 可以 `confirm`；
- `confirmed` 不允许 `confirm` / `reject` / `ignore`；
- `confirmed` 可以 `close`；
- `closed` 不允许 `confirm` / `reject` / `ignore` / `close`；
- `closed` 仍允许 `add_comment`。

这个测试用于保证 7 号窗口复核状态机在 8 号窗口接口统一响应改造后没有被破坏。

---

### 3.3 review chinese fields 测试

文件：

```text
tests/review/test_review_chinese_fields.py
```

验证目标：

- `assigned_to` 可以保存中文；
- `created_by` 可以保存中文；
- `reviewer` 可以保存中文；
- `remark` 可以保存中文；
- `export` 导出结果中文字段不乱码。

重点防止 MySQL、接口、导出结构中出现中文乱码。

---

## 四、运行 pytest

运行全部正式测试：

```bash
pytest tests -q
```

当前 8 号窗口验收结果：

```text
6 passed in 0.61s
```

说明：

> 当前 `tests/` 下正式测试全部通过。

---

## 五、运行 review 专项测试

运行 review 测试：

```bash
pytest tests\review -q
```

当前结果：

```text
全部通过
```

当前 review pytest 覆盖：

- 统一响应契约；
- `trace_id` 非空；
- 状态机流转；
- 中文字段存储与导出。

---

## 六、运行 5号窗口 smoke test

命令：

```bash
python -m scripts.smoke_test_window5_rag_explanation
```

当前 8 号窗口验收结果：

```text
PASS: 9
FAIL: 0
SKIP: 0
```

覆盖能力：

- baseline 检索；
- vector 检索；
- hybrid 检索；
- 低价规则解释链；
- 跨平台价差规则解释链；
- 规格风险规则解释链；
- evidence / citation 输出。

重点结果：

```text
spec_risk 命中解释链通过
audit_result_id = 259
evidences = 5
citations = 2
```

---

## 七、运行 6号窗口 smoke test

命令：

```bash
python -m scripts.smoke_test_window6_ask_orchestration
```

当前 8 号窗口验收结果：

```text
PASS: 6
FAIL: 0
```

覆盖能力：

- `/ask analysis` 路由；
- `/ask retrieval` 正式检索服务；
- `/ask explanation` 正式解释链；
- `/ask explanation fallback` 兼容链；
- `/ask mixed` 受控编排链；
- `/ask-lc mixed` 增强链。

重点说明：

- `/ask` 是正式主链，强调稳定可控；
- `/ask-lc` 是增强链，强调 tool calling 展示能力。

---

## 八、运行 7号窗口 smoke test

---

### 8.1 人工复核闭环

命令：

```bash
python -m scripts.smoke_test_window7_review_flow
```

当前结果：

```text
PASS: 7
FAIL: 0
```

覆盖能力：

- 创建复核任务；
- 查询任务列表；
- 查询任务详情；
- 添加备注；
- 确认异常；
- 查询复核记录；
- 导出复核结果。

---

### 8.2 中文字段验收

命令：

```bash
python -m scripts.smoke_test_window7_review_chinese
```

当前结果：

```text
通过
```

覆盖能力：

- `assigned_to` 中文；
- `reviewer` 中文；
- `remark` 中文；
- 导出中文字段；
- API 返回不出现 `???`。

---

### 8.3 复核状态机

命令：

```bash
python -m scripts.smoke_test_window7_review_state_machine
```

当前结果：

```text
PASS: 6
FAIL: 0
```

覆盖能力：

- `pending -> confirmed` 允许；
- `confirmed` 状态下禁止 `confirm / reject / ignore`；
- `confirmed -> closed` 允许；
- `closed` 状态下禁止所有状态动作；
- `closed` 状态下仍允许 `add_comment`。

---

## 九、当前推荐完整测试顺序

本地开发环境推荐按以下顺序执行：

```bash
pytest tests -q

python -m scripts.smoke_test_window5_rag_explanation
python -m scripts.smoke_test_window6_ask_orchestration
python -m scripts.smoke_test_window7_review_flow
python -m scripts.smoke_test_window7_review_chinese
python -m scripts.smoke_test_window7_review_state_machine
```

推荐原因：

1. 先跑 pytest，确认正式测试集没问题；
2. 再跑 5 / 6 / 7 smoke test，确认核心业务主链没有断。

---

## 十、测试前置条件

运行上述 smoke test 前，需要确保：

- FastAPI 服务已启动；
- MySQL 数据库可连接；
- Alembic 迁移已完成；
- 基础业务样本已存在；
- `SPEC_RISK` 正向样本已存在；
- `audit_result_id=259` 可用。

本地服务启动示例：

```bash
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

---

## 十一、Docker 环境下的测试说明

当前 Docker Compose 可以完成：

- 镜像构建；
- MySQL 启动；
- Alembic 自动迁移；
- API 启动；
- `/docs` 访问；
- `/openapi.json` 访问；
- 基础接口访问。

但 Docker 新库默认是空业务库，不一定包含完整 smoke test 所需数据。

因此，以下测试不建议直接在 Docker 空库中执行：

```bash
python -m scripts.smoke_test_window5_rag_explanation
python -m scripts.smoke_test_window6_ask_orchestration
python -m scripts.smoke_test_window7_review_flow
```

原因：

> 这些测试依赖完整业务样本、`audit_result`、`rule_hit`、`SPEC_RISK` 正向样本等数据。

Docker 空库下推荐优先验证：

```bash
curl.exe http://127.0.0.1:8000/

curl.exe "http://127.0.0.1:8000/api/v1/reviews/tasks?page=1&page_size=5"
```

---

## 十二、当前 8号窗口测试验收结果

当前已完成以下测试验收：

| 测试项                        | 结果                         |
|----------------------------|----------------------------|
| `pytest tests -q`          | `6 passed`                 |
| 5号窗口 RAG / 规则解释 smoke test | `PASS 9 / FAIL 0 / SKIP 0` |
| 6号窗口 `/ask` 编排 smoke test  | `PASS 6 / FAIL 0`          |
| 7号窗口人工复核闭环 smoke test      | `PASS 7 / FAIL 0`          |
| 7号窗口中文字段 smoke test        | 通过                         |
| 7号窗口状态机 smoke test         | `PASS 6 / FAIL 0`          |

---

## 十三、本阶段结论

当前项目已经具备基础测试收口能力：

- 正式 pytest 测试可运行；
- 核心 review API 契约可验证；
- 复核状态机可验证；
- 中文字段可验证；
- 5 / 6 / 7 主链 smoke test 可运行；
- Docker 基础接口可验证。

当前测试体系已经满足 8 号窗口第一阶段要求：

> 不是只靠手点验证，而是有 pytest + smoke test 双层验证。

后续如需进一步企业级增强，可以继续补充：

- 测试数据库隔离；
- pytest fixture 自动造数；
- API TestClient 测试；
- CI 自动执行测试；
- Docker 演示数据 seed；
- 覆盖率统计。