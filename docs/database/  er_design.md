数据库 ER 逻辑设计（2号窗口正式版）

1. 文档目的

本文档用于定义鸿茅药酒电商维价审核 Copilot 在 2号窗口：数据库与数据模型阶段 的核心实体关系设计，明确系统后续正式数据底盘的承载方式。
本阶段职责不是去重写规则引擎、RAG、/ask 编排或人工复核页面，而是先把这些能力未来要落的数据对象、关系边界、承载层次定清楚。

本设计同时遵循以下前提：

已按 1 号窗口完成正式工程骨架重构，docs/database/、alembic/、app/schemas/、app/repositories/ 等数据库相关落点已经预留完成。
当前旧系统中的 legacy_sqlite.py 仅作为 原型阶段过渡数据底盘 / 旧结果层参考来源，不能直接翻译成未来正式数据库方案。
正式数据库设计必须承接旧结果层已形成的关键业务字段口径，例如“标准化品牌、规范化规格、干净平台、干净价格、显式低价阈值、组内均价、当前价格/组均价比、低价规则来源、异常原因”等，避免后续出现“数据库说东，结果层说西”。

2. 本阶段设计目标

本 ER 设计的目标不是“先有个库”，而是让后续 4～7 号窗口都有正式落点。根据总要求与验收标准，数据库层至少要能正式支撑以下对象：

原始商品数据
清洗与归一结果
异常审核结果
规则定义
规则文档切块
人工复核任务
人工复核记录
问答请求日志
模型调用日志

对应到正式核心表，即：

product_raw
product_clean
audit_result
rule_definition
rule_chunk
review_task
review_record
ask_log
model_call_log

3. 设计原则
   3.1 先业务分层，再技术落库

数据库设计必须围绕维价审核业务链路展开，而不是继续沿用“第二周三张预览表”的阶段产物思路。当前旧 SQLite 里存在
cleaned_products、normalized_products、anomaly_details、pipeline_runs 等原型表，它们能说明旧系统依赖什么，但不应直接作为正式表结构模板。

3.2 正式表统一英文蛇形命名

正式数据库字段统一使用英文蛇形命名；中文字段可以保留在展示层、导出层、报表层，但不进入正式表结构。这也符合 1 号窗口交接中已经明确的正式口径。

3.3 清洗层与结果层必须拆开
清洗与归一属于 product_clean
异常判定与命中依据属于 audit_result

不能把所有字段都堆到一个“大结果表”里，否则后续规则解释、复核闭环和 ask 编排都会变脏。

3.4 规则本体与解释素材必须拆开
rule_definition：规则本体与业务配置
rule_chunk：规则文档切块与解释素材

因为 5 号窗口的 RAG 解释系统要求“依据能追到具体文档 / chunk / metadata”，但解释层又不能覆盖 4 号窗口的结果层事实。

3.5 任务与记录必须拆开
review_task：任务对象、状态、归属
review_record：动作留痕、备注、操作历史

这是后续人工复核闭环成立的基本前提。总验收也明确要求“业务人员不仅能看，还能做判断、写备注、留记录、改状态、导出结果”。

3.6 ask 日志与模型调用日志必须拆开
ask_log：一次业务问答主请求
model_call_log：该请求内部某次模型调用明细

因为 ask 链路和模型调用链路不是同一个粒度。总要求已明确两者都应作为重点表独立承载。

4. 核心业务链路与数据分层

本项目新版主链应能表现为：

原始商品数据 → 清洗标准化 → 异常判定 → 规则解释 / 问答编排 → 人工复核 → 留痕 / 导出。

基于这条主链，数据库逻辑上应拆为 6 层：

4.1 原始数据层

承载采集上来的平台原始商品记录。
对应表：product_raw

4.2 清洗归一层

承载品牌归一、规格归一、平台清洗、价格清洗后的结果。
对应表：product_clean

4.3 审核结果层

承载异常事实、规则命中、阈值依据、原因说明。
对应表：audit_result

4.4 规则知识层

承载规则定义本体和规则解释素材。
对应表：rule_definition、rule_chunk

4.5 复核闭环层

承载复核任务、复核动作、状态流转留痕。
对应表：review_task、review_record

4.6 问答审计层

承载 ask 请求日志与模型调用日志。
对应表：ask_log、model_call_log

5. ER 总体结构

下面给出第一版正式 ER 逻辑关系：

product_raw
└── 1:N ──> product_clean
└── 1:N ──> audit_result
└── 1:N ──> review_task
└── 1:N ──> review_record

rule_definition
└── 1:N ──> rule_chunk

audit_result
└── N:1 ──> rule_definition （命中主规则，可空）

ask_log
└── 1:N ──> model_call_log

ask_log
└── N:1 ──> audit_result （可选，表示本次问答关联的审核结果）

review_task
└── N:1 ──> audit_result

6. 各核心实体说明
   6.1 product_raw
   定位

原始商品数据表，用于保存采集回来的平台原始记录。

为什么单独存在

旧系统原型阶段直接把 CSV 写入 SQLite，并在后续查询中更多依赖清洗后表与异常表。正式系统里必须保留原始态，才能支撑后续复盘、审计、字段重跑与口径修正。

典型承载内容
原始标题
原始规格文本
原始价格文本 / 值
平台来源
店铺来源
商品链接
抓取时间
原始 payload
6.2 product_clean
定位

清洗与归一结果表，用于承接原始数据标准化后的业务可用结果。

为什么存在

旧系统里 cleaned_products 与 normalized_products 分别承载了这类中间层结果，但正式系统不应继续沿用原型阶段表名，而应统一纳入“清洗归一层”。

必须承接的旧口径

以下旧字段应在该层正式承接：

标准化品牌 → standardized_brand
规范化规格 → normalized_spec
干净平台 → clean_platform
干净价格 → clean_price
干净标题 → clean_title
干净规格 → clean_spec
标题规范提示 → 可进入 normalize_note 或类似字段
6.3 audit_result
定位

审核结果表，用于承接异常判定后的正式业务事实。

为什么它是核心骨头

4 号窗口后面要做的不是“再跑一遍脚本”，而是把“异常为什么成立”变成系统事实。
因此 audit_result 必须能回答：

是否异常
异常类型
命中规则
规则版本
输入值
阈值 / 比较依据
最终判定原因
必须承接的旧口径

以下旧字段应正式迁入该层：

显式低价阈值 → explicit_low_price_threshold
组内均价 → group_avg_price
当前价格/组均价比 → price_to_group_avg_ratio
低价规则来源 → low_price_rule_source
异常原因 → reason_text
与规则表关系

audit_result 可以通过 rule_definition_id 指向命中的主规则；若某些复合异常命中多条规则，后续可再扩展 audit_rule_hit
关联表，但本期先不主写，避免 2 号窗口过度扩张。

6.4 rule_definition
定位

规则定义表，用于承载正式业务规则本体。

作用

它回答的是：

规则叫什么
属于哪类规则
当前版本是多少
是否启用
阈值配置是什么
生效时间是什么时候
为什么必须独立

因为正式规则引擎要求“规则配置化、规则版本化、规则命中留痕”，不能继续只散落在 if-else 中。

6.5 rule_chunk
定位

规则文档切块表，用于承载规则解释系统的文档级证据素材。

作用

它服务于 5 号窗口的 RAG 解释能力，回答的是：

这段依据来自哪份文档
属于哪个标题 / 章节
是第几个 chunk
metadata 是什么
后续向量索引引用的是哪段内容
为什么不能和 rule_definition 合并

因为规则本体是“业务定义对象”，chunk 是“解释检索素材对象”。一个管规则是什么，一个管证据怎么找。两者混在一起，后面解释层一定会脏。

6.6 review_task
定位

人工复核任务表，用于承接“某条异常是否需要业务复核、当前处于什么状态、由谁处理”。

作用

后续 7 号窗口的异常列表页、状态流转、任务归属、本轮待办，本质都依赖这张表。

为什么必须独立

因为“异常本身”不等于“复核任务”。
一条异常结果可以生成一个待处理任务，也可以后续关闭、分配、延期、导出。任务语义必须独立。

6.7 review_record
定位

人工复核动作记录表，用于承接具体操作留痕。

作用

它回答的是：

谁做了动作
做了什么动作
写了什么备注
当时看到了什么依据
操作发生在什么时候
为什么必须独立

总验收已经明确：人工复核闭环不是“能看页面”，而是必须能看、能点、能改、能留痕。没有动作记录表，所谓复核闭环就是空壳。

6.8 ask_log
定位

问答主请求日志表，用于记录一次 /ask 请求的整体输入输出。

为什么它必须承接现有接口口径

当前 app/schemas/ask.py 已经把 ask 响应合同定成：

route
answer
tools_used
analysis_result
retrieval_result
explanation_result
trace

因此正式日志表不能完全另起炉灶，必须围绕这组字段承接。

作用

后续 6 号窗口落 ask 编排留痕、7 号窗口关联业务查询、8 号窗口做接口回归，都会依赖这张表。

6.9 model_call_log
定位

模型调用日志表，用于记录 ask 链路内部某一次具体模型调用。

为什么不能和 ask_log 合并

因为 ask 是“请求粒度”，模型调用是“步骤粒度”。
一条 ask 可能包含分类、解释、总结、tool-calling 等多个模型调用。
若不拆开，后面 trace、性能分析、错误排查都会变成一团。

7. 旧系统原型表到正式实体的映射关系

当前 legacy_sqlite.py 中旧原型表包括：

cleaned_products
normalized_products
anomaly_details
pipeline_runs

正式系统不建议原封不动继承，建议映射如下：

7.1 cleaned_products

映射到：

product_raw（部分原始字段）
product_clean（清洗字段）
7.2 normalized_products

映射到：

product_clean
7.3 anomaly_details

映射到：

product_clean（清洗归一相关字段）
audit_result（异常事实相关字段）
7.4 pipeline_runs

不作为正式核心业务表主写，可在后续 3 号或 8 号窗口中视需要扩展为批次审计 / pipeline_job / import_log 等基础设施表。
本期先不把它列为正式主干表，避免 2 号窗口过度扩张。

8. 已识别的关键口径风险
   8.1 旧 SQLite 路径口径存在漂移

目录树显示旧 SQLite 当前实际位于 data/legacy/price_audit.db，但 legacy_sqlite.py 中默认路径函数仍指向
data/price_audit.db。这说明旧兼容层路径口径尚未完全统一。后续迁移文档必须明确以哪一份为正式迁移来源。

8.2 兼容层不能继续写厚

当前项目中 legacy_sqlite.py 是过渡层，app/core/schemas.py 等也属于兼容或预留性质。2 号窗口之后，正式数据库模型应逐步转入
app/models/ 与数据库专属 schema 文件，避免继续把兼容层写成主实现。

8.3 不允许直接把 SQLite 翻译成 MySQL

总设计与 1 号交接都明确反对这种偷懒做法。2 号窗口要做的是业务建模，而不是“旧表换个数据库方言”。

9. 本文档对应的后续落地范围

本 ER 文档确定后，2 号窗口后续应继续落以下内容：

docs/database/table_design.md
docs/database/migration_plan.md
app/models/ 正式 ORM 模型
app/schemas/audit.py
app/schemas/review.py
app/schemas/rule.py
app/schemas/log.py

10. 一句话总结

本 ER 设计的核心结论是：

正式数据库不再围绕“第二周三张原型表”组织，而是围绕“原始数据、清洗归一、审核事实、规则本体、解释素材、复核任务、复核记录、问答日志、模型调用日志”九类正式业务对象组织。