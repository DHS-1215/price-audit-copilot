# Price Audit Copilot

一个基于 FastAPI 和 Ollama 构建的电商价格异常审核辅助系统。

## 项目简介

Price Audit Copilot 面相电商商品价格审核场景，目标是把爬取后的原始数据商品做成一个可被业务直接使用的AI辅助系统。
项目当前聚焦于“价格异常审核”这一真实业务问题，逐步实现以下能力：

- 商品标题结构化抽取
- 原始商品数据清洗
- 品牌和规格归一化
- 价格异常识别
- 轻量数据库落库
- 为后续规则解释、RAG检索和统一问答入口打基础

## 第一周已完成内容

- 完成 FastAPI 后端最小骨架搭建
- 接通 Ollama 本地模型调用
- 实现 '/ask' 问答接口
- 实现 '/extract' 商品标题结构化抽取接口
- 可通过 Swagger 文档直接调用接口
- 已准备样例商品数据集

## 第二周已完成内容

第二周重点不是“接口能不能跑”，而是让系统开始具备真实业务判断能力。

## 本地运行方式
pip install -r requirements.txt
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001
