# Price Audit Copilot

一个基于 FastAPI 和 Ollama 构建的电商价格异常审核辅助系统。

## 项目简介

这个项目面向电商商品价格审核场景，目标是把原始商品数据做成一个可被业务使用的 AI 辅助系统。

当前阶段已支持：

- 商品标题结构化抽取
- 基础问答接口
- 本地模型调用
- 为后续价格异常识别打基础

## 第一周已完成内容

- 完成 FastAPI 后端最小骨架搭建
- 接通 Ollama 本地模型调用
- 实现 `/ask` 问答接口
- 实现 `/extract` 商品标题结构化抽取接口
- 可通过 Swagger 文档页直接调试接口
- 已准备样例商品数据集

## 技术栈

### 已实现
- Python
- FastAPI
- Ollama
- Pydantic
- Requests
- Git / GitHub

## 当前接口说明
- `GET /`：服务健康检查
- `POST /ask`：调用本地模型进行基础问答
- `POST /extract`：从商品标题中抽取结构化字段

### 计划在后续周次实现
- Pandas（第二周）
- SQLite / MySQL（第二周，先做轻量存储）
- 数据清洗与归一化（第二周）
- 规则异常识别（第二周）
- RAG / 检索增强（第三周）
- Chroma / FAISS（第三周）
- LangChain（第三至第四周接入）
- LangGraph（第四周后视流程复杂度接入）
- 自然语言查数与分析入口（第四周）
- Streamlit（第五周）
- Docker（第六周）
- 评测与结果验证（第六周）

## 本地运行方式
pip install -r requirements.txt
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001