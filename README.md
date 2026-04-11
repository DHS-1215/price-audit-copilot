# Price Audit Copilot

一个基于 FastAPI 和 Ollama 构建的电商价格异常审核辅助系统。

## 项目简介

Price Audit Copilot 面向电商商品价格审核场景，目标是把爬取后的原始数据商品做成一个可被业务直接使用的AI辅助系统。
项目当前聚焦于“价格异常审核”这一真实业务问题，逐步实现以下能力：

- 商品标题结构化抽取
- 原始商品数据清洗
- 品牌和规格归一化
- 价格异常识别
- 轻量数据库落库
- 为后续规则解释、RAG检索和统一问答入口打基础

## 技术栈

### 已实现

- Python（第一周）
- FastAPI（第一周）
- Ollama（第一周）
- Pydantic（第一周）
- Requests（第一周）
- Pandas（第二周）
- SQLite（第二周）
- Git / GitHub（第一周）
- 规则知识库与 FAQ（第三周）
- RAG / 检索增强 baseline（第三周）
- Embedding + 向量库检索（第三周收口 / 第四周前完成）
- FAISS（第三周）
- LangChain（第三至第四周接入）
- 自然语言查数与分析入口（第四周）
- baseline / FAISS 双模式检索接入统一入口（第四周）
- langchain-ollama（第四周）

### 计划在后续周次实现

- Streamlit（第五周）
- Docker（第六周）
- 评测与结果验证（第六周）

## 第一周已完成内容

- 完成 FastAPI 后端骨架搭建
- 接通 Ollama 本地模型调用
- 实现 '/ask' 问答接口
- 实现 '/extract' 商品标题结构化抽取接口
- 可通过 Swagger 文档直接调用接口
- 已准备样例商品数据集

## 第二周已完成内容

第二周重点不是“接口能不能跑”，而是让系统开始具备真实业务判断能力。

### 1.数据清洗

已完成商品样本数据的基础清洗， 包括：

- 商品标题清洗
- 规格字段基础清洗
- 价格字段清洗与数值化
- 平台字段归并
- 日期字段标准化
- 缺失值与异常值基础标记

对应模块：app/data/cleaner.py
输出文件：data/cleaned_products_preview.csv

### 2.品牌和规格归一化

已完成商品品牌与规格归一化处理，包括：

- 品牌别名统一
- 规格写法统一
- 从标题中提取规格提示
- 标记标题规格与规格列是否不一致
- 生成标准化后的商品数据结果

对应模块：app/data/normalizer.py
输出文件：data/normalized_products_preview.csv

### 3.异常规则分析

已完成第二周核心业务规则，包括：

- 疑似异常低价识别
- 跨平台价差过大识别
- 规格识别风险识别
- 异常原因生成
- 异常明细输出

其中低价规则采用双轨方式：

- 显式业务阈值规则
- 统计规则兜底（同品牌 + 同规格组内均价对比）

对应模块：app/tools/analysis_tools.py
输出文件：data/异常明细.csv

### 4.轻量数据库落库

已完成第二周轻量存储层建设，使用 SQLite 对阶段结果进行落库，便于后续查询、统计和问答能力扩展。

已落库内容包括：

- 清洗结果
- 标准化结果
- 异常分析结果

对应模块：app/data/db.py
数据库文件：data/price_audit.db

### 5.第二周当前可回答问题

当前系统已经可以支持以下基础业务问题：

- 哪些商品是疑似异常低价
- 哪些商品规格识别有风险
- 哪个平台低价最多
- 哪个品牌跨平台价差最大

## 第三周已完成内容

第三周的重点不是继续扩异常规则，也不是先做前端，而是给第二周已经形成的“异常结果层”补上一层“依据解释层”。

一句话概括：

> 让系统从“会判异常”，升级成“会解释为什么这样判”。

### 1. 规则知识库与 FAQ

已新增规则知识库目录 `data/rules/`，并完成首批规则文档与 FAQ 编写，包括：

- 平台价格审核规则
- 规格归一与规格风险识别规则
- 低价异常判定规则
- 跨平台价差判定规则
- 人工复核流程说明
- FAQ 问答集

当前规则文档目录：

- `data/rules/platform_price_rules.md`
- `data/rules/spec_normalization_rules.md`
- `data/rules/low_price_detection_rules.md`
- `data/rules/cross_platform_gap_rules.md`
- `data/rules/manual_review_process.md`
- `data/rules/faq.md`

### 2. 规则文档 ingest

已完成规则文档导入与切分模块。  
对应模块：`app/rag/ingest.py`

当前能力包括：

- 读取 `data/rules/` 下的 markdown 规则文档
- 进行基础文本清洗
- 按 markdown 标题切 section
- 按段落切 chunk
- 生成规则知识库中间产物

当前输出文件：

- `data/rag/rule_chunks.jsonl`
- `data/rag/rule_manifest.json`

当前 ingest 结果：

- 规则文档数量：6
- chunk 数量：43

### 3. baseline 规则检索器

已完成第三周 baseline 版本的规则检索器。  
对应模块：`app/rag/retriever.py`

当前检索逻辑采用：

- 业务路由
- 关键词匹配
- 可解释打分

当前能力包括：

- 输入问题
- 从规则 chunk 中检索相关片段
- 返回 top-k 规则证据
- 展示命中原因，便于调试与后续优化

当前这版 retriever 的定位是：

> 第三周的 baseline 检索器，用于先验证规则文档结构、chunk 设计和解释链路是否通顺。

### 4. 规则检索工具层

已完成规则检索工具层封装。  
对应模块：`app/tools/retrieval_tools.py`

当前能力包括：

- 输出规则主题
- 输出关键词与优先文档
- 输出证据列表
- 输出证据摘要与上下文文本

该模块的作用是把底层 retriever 的结果整理成后面统一问答入口可直接调用的工具输出。

### 5. 解释链工具层

已完成第三周解释链工具层。  
对应模块：`app/tools/explanation_tools.py`

当前能力包括：

- 读取第二周结果层关键字段
- 自动生成更适合规则检索的问题
- 调用规则检索工具获取依据
- 拼接结果层事实、规则层摘要和复核建议
- 输出一段完整解释

当前解释链遵循一个关键原则：

> 先尊重第二周结果层，再补第三周规则层依据。

例如低价异常解释时，必须先看：

- `是否疑似异常低价`
- `低价规则来源`
- `组内均价`
- `当前价格/组均价比`
- `异常原因`

不能跳过结果层直接靠规则文档自己解释。

### 6. 向量检索版（FAISS）

在 baseline 检索基础上，第三周进一步补充了向量检索版，实现了更完整的 RAG 检索能力。  
对应模块：

- `app/rag/faiss_store.py`
- `app/rag/faiss_retriever.py`

当前方案采用：

- Ollama embedding 模型：`qwen3-embedding`
- 本地向量索引：FAISS

当前能力包括：

- 读取规则 chunk
- 调用 Ollama embedding 接口生成向量
- 本地构建 FAISS 索引
- 对规则问题进行语义检索
- 返回 top-k 相似规则片段

该版本的定位是：

> 第三周高质量收口的向量检索版，用于补强 baseline 检索在语义召回上的不足。

### 7. 第三周正式验收

已补充第三周正式验收样例与验收记录：

- `data/eval/week3_acceptance_cases.md`
- `data/eval/week3_acceptance_results.md`

当前验收覆盖两组内容：

#### A组：规则检索验收

- 低价规则检索
- 跨平台价差规则检索
- 规格与标题不完整规则检索
- 人工复核规则检索

#### B组：解释链验收

- 统计低价解释
- 显式阈值低价解释
- 低价 + 跨平台双异常解释
- 规格风险解释

当前第三周正式验收结果：

- A组：全部通过
- B组：全部通过

### 8. 第三周当前可演示能力

当前系统已经可以演示以下问题：

#### 规则检索类

- 为什么这个商品会被判成疑似异常低价？
- 跨平台价差异常是怎么判的？
- 如果标题不完整，规则上该怎么处理？
- 人工复核时应该先看什么？

#### 解释链类

给定一条异常样本记录，系统可以输出：

- 结果层事实说明
- 规则层依据摘要
- 复核建议
- 一段完整解释文本

#### 向量检索类

系统已经支持基于 embedding + FAISS 的规则语义检索，可与 baseline 检索做对比。

### 9. 第三周检索方案对比与下一步方向

已新增第三周检索方案对比总结：

- `data/eval/week3_retrieval_comparison.md`

当前结论是：

- baseline 检索更适合规则型、可控型问题
- 向量检索更适合语义型、自然问句型问题
- 两者不是替代关系，而是更适合在第四周走 hybrid 检索路线

即：

> baseline 更像“稳”，vector 更像“宽”。

### 10. 第三周设计取舍

第三周没有一开始就直接上向量检索，而是先做了一版 baseline retriever。

原因是：

- 先验证规则文档内容是否合理
- 先验证 chunk 切分是否合理
- 先验证 FAQ 和主规则文档能否支撑解释链
- 先把“结果层 -> 规则层 -> 复核建议”这条链跑通

这样做的好处是：

- 更容易调试
- 更容易理解
- 更容易定位问题
- 便于后续升级成 embedding + 向量库版检索

在 baseline 跑通后，第三周再补上向量检索版，形成了：

- baseline 检索
- 向量检索
- 解释链

因此第三周当前版本更准确的定位是：

> 规则知识库 + baseline retriever + 向量检索 + 解释链，为第四周统一问答入口打下基础。

## 第四周已完成内容

第四周的重点不是继续扩底层规则，也不是先做前端，而是把前几周已经形成的能力整合成一个统一问答入口，让系统开始更像一个真正可用的
Copilot。

一句话概括：

> 让系统从“多个独立能力模块”，升级成“具备统一 ask 入口的 Copilot 原型”。

### 1. 统一 ask 入口

已完成统一问答入口。  
对应模块：`app/api/routes_ask.py`

当前统一入口支持以下问题类型：

- 数据分析类问题
- 规则检索类问题
- 异常解释类问题
- 混合问答类问题

当前能力包括：

- 自动识别问题类型
- 根据问题路由到不同工具
- 返回统一结构结果
- 输出工具调用 trace

当前 `/ask` 返回结果已统一包含以下字段：

- `route`
- `answer`
- `tools_used`
- `analysis_result`
- `retrieval_result`
- `explanation_result`
- `trace`

这意味着第四周已经不再只是“分别调用几个模块”，而是开始具备统一调度能力。

### 2. 汇报生成工具层

已完成汇报生成工具层封装。  
对应模块：`app/tools/report_tools.py`

当前能力包括：

- 根据数据分析结果生成简短汇报
- 根据规则检索结果补充规则依据说明
- 自动拼接复核建议
- 为 mixed 问题输出更适合业务阅读的说明文本

该模块的作用是：

> 把 analysis / retrieval / explanation 的结果，组织成更像业务汇报的话术输出。

这使系统开始具备“从结果到说明”的能力，而不只是返回原始 JSON。

### 3. 工具调用日志落盘

已完成统一 ask 入口的日志落盘能力。  
对应模块：`app/tools/log_tools.py`

当前能力包括：

- 记录每次 `/ask` 调用时间
- 记录用户问题
- 记录问题路由结果
- 记录实际调用工具
- 记录最终回答
- 记录 trace 链路
- 将结果追加写入本地 JSONL 日志文件

当前日志文件：

- `data/outputs/ask_logs.jsonl`

这一步的意义是：

> 让统一问答入口具备最基础的可追踪能力，便于调试、验收和后续前端展示。

### 4. baseline / FAISS 双模式检索接入统一入口

第四周在第三周规则检索能力基础上，进一步完成了双模式检索接入统一 ask 入口。  
对应模块：

- `app/tools/retrieval_tools.py`
- `app/tools/explanation_tools.py`
- `app/rag/faiss_retriever.py`

当前统一入口已经支持：

- `baseline` 检索模式
- `faiss` 向量检索模式

当前能力包括：

- 在规则检索类问题中切换 baseline / FAISS
- 在异常解释类问题中切换 baseline / FAISS
- 在 mixed 问题中切换 baseline / FAISS
- 在返回结果中标记当前检索模式

当前第四周对比结论是：

- baseline 更适合规则型、可控型问题
- FAISS 更适合自然语言、FAQ 风格问题
- baseline 更像“稳”
- FAISS 更像“宽”

对应对比文档：

- `data/eval/week4_retrieval_comparison.md`

### 5. 第四周正式验收

已补充第四周统一 ask 入口的验收用例与验收结果：

- `data/eval/week4_acceptance_cases.md`
- `data/eval/week4_acceptance_results.md`

当前验收覆盖内容包括：

#### A组：数据分析类

- 近7天哪个平台异常低价最多

#### B组：规则检索类

- 如果标题不完整，规则上该怎么处理

#### C组：异常解释类

- 为什么这个商品会被判成高风险

#### D组：混合问答类

- 先找出低价商品，再按规则给我写一段简短汇报

#### E组：附加能力验收

- 统一返回结构
- 问答日志落盘

当前第四周验收结论：

- analysis：通过
- retrieval：通过
- explanation：通过
- mixed：通过
- 日志落盘：通过

这说明第四周手写编排版统一 ask 入口已经完成第一轮正式收口。

### 6. LangChain 正式接入

在完成手写编排版 `/ask` 后，第四周进一步补充了 LangChain 正式接入。  
对应模块：

- `app/chain/langchain_tools.py`
- `app/chain/ask_agent.py`
- `app/api/routes_ask_langchain.py`

新增接口：

- `POST /ask-lc`

当前 LangChain 接入内容包括：

- 将现有业务函数封装成 LangChain tools
- 基于 Ollama + LangChain 构建 agent 调度链
- 支持 analysis / retrieval / explanation 问题的 tool calling
- mixed 场景最终采用“LangChain + 受控汇报流程”的方式处理

当前 LangChain 版能力验证结论：

- analysis：通过
- retrieval：通过
- explanation：通过
- mixed：通过（采用受控流程）

对应记录文档：

- `data/eval/week4_langchain_integration.md`

这意味着第四周最终形成了两条并行能力：

- 手写编排版 `/ask`
- LangChain 版 `/ask-lc`

它们的定位分别是：

- `/ask`：更稳，更适合结果可控与正式验收
- `/ask-lc`：更适合展示 tool calling 与模型调工具能力

### 7. 第四周当前可演示能力

当前系统已经可以演示以下问题：

#### 数据分析类

- 近7天哪个平台异常低价最多？
- 当前低价样本有哪些？

#### 规则检索类

- 如果标题不完整，规则上该怎么处理？
- 低价异常规则是怎么定义的？

#### 异常解释类

- 为什么这个商品会被判成高风险？
- 为什么这个商品会被判成疑似异常低价？

#### 混合问答类

- 先找出低价商品，再按规则给我写一段简短汇报。

这说明项目已经从第三周的“规则依据解释层”，进一步升级到了第四周的“统一问答入口层”。

### 8. 第四周设计取舍

第四周没有一开始就直接把所有问题都交给 LangChain 自由 agent 处理，而是先完成了一版手写编排版统一 ask 入口。

这样做的原因是：

- 先保证业务主链稳定
- 先让 analysis / retrieval / explanation / mixed 四类问题跑通
- 先建立统一输出结构
- 先建立日志与验收体系

在手写版完成验收后，再补上 LangChain 正式接入。

第四周进一步验证了一个结论：

- 自由 agent 在 analysis / explanation 场景下表现较稳
- retrieval 场景更容易出现标题级证据扩写
- mixed 场景在真实业务里不适合完全交给自由 agent 猜流程

因此第四周当前更准确的定位是：

> 手写编排版统一 ask 入口 + LangChain 正式接入，为第五周前端展示与工作流扩展打下基础。

## 本地运行方式

```bash
pip install -r requirements.txt
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001
