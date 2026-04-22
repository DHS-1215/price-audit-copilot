数据库表结构设计（2号窗口正式版）

1. 文档目的

本文档用于在 ER 逻辑设计基础上，进一步明确鸿茅药酒电商维价审核 Copilot 的核心表结构设计方案。
本阶段目标不是补业务逻辑，而是把后续 4～7 号窗口要落的数据对象、字段口径、主外键关系、状态字段和版本字段先定稳。

当前项目已经具备：

正式工程骨架
docs/database/、alembic/、app/schemas/ 等落点
旧 SQLite 兼容层 legacy_sqlite.py
已拆分的接口层 schema (ask.py / common.py / extract.py)

但目前 app/models/ 目录尚未创建，因此本表设计文档也将作为后续 ORM 落地的直接依据。

2. 表设计总原则
   2.1 正式表统一英文蛇形命名

正式数据库表名、字段名统一使用英文 snake_case。
中文字段只用于：

展示层
导出层
报表层

不进入正式表结构。这个口径已在 1 号窗口交接中明确。

2.2 原始层、清洗层、结果层必须拆开

旧 SQLite 中 cleaned_products、normalized_products、anomaly_details 反映的是原型阶段处理结果，不适合直接照搬为正式表。正式设计必须拆成：

product_raw
product_clean
audit_result
2.3 规则定义与规则解释素材必须拆开
rule_definition：规则本体
rule_chunk：规则文档切块与解释素材

避免后续 5 号窗口 RAG 解释和 4 号窗口规则判定互相污染。

2.4 任务与记录必须拆开
review_task：当前任务状态
review_record：动作留痕

这也是后续人工复核闭环成立的前提。

2.5 ask 日志与模型调用日志必须拆开
ask_log：一次请求
model_call_log：一次请求内部的某次模型调用

这是为了满足 trace、日志、审计和排障要求。

3. 核心表总览

本期正式核心表共 9 张：

product_raw
product_clean
audit_result
rule_definition
rule_chunk
review_task
review_record
ask_log
model_call_log

4. 各表详细设计
   4.1 product_raw
   4.1.1 表定位

原始商品数据表，承载采集上来的原始商品记录。

4.1.2 设计说明

该表用于保留未经清洗的原始事实，后续清洗、归一、审核都基于它展开。
正式系统必须保留原始态，不能只存“洗完之后的结果”，否则后续复盘和字段重跑没有抓手。这个问题在旧 SQLite 原型方案里是不够正式的。

4.1.3 字段设计
字段名 类型建议 必填 说明
id BIGINT PK 是 主键
batch_no VARCHAR(64)    是 采集批次号
source_platform VARCHAR(64)    是 来源平台
source_shop_name VARCHAR(255)    否 来源店铺名
source_product_title VARCHAR(1000)    是 原始商品标题
source_spec_text VARCHAR(255)    否 原始规格文本
source_price_text VARCHAR(255)    否 原始价格文本
source_price_value DECIMAL(10,2)    否 解析出的原始价格值
product_url VARCHAR(1000)    否 商品链接
sku_id VARCHAR(128)    否 商品 SKU 或平台侧标识
capture_time DATETIME 否 抓取时间
source_payload_json JSON 否 原始扩展载荷
ingest_source VARCHAR(64)    否 导入来源，如 rpa/csv/api
created_at DATETIME 是 创建时间
4.1.4 索引建议
idx_product_raw_batch_no (batch_no)
idx_product_raw_platform_capture (source_platform, capture_time)
idx_product_raw_sku_id (sku_id)
4.2 product_clean
4.2.1 表定位

清洗与归一结果表，承载品牌归一、规格归一、平台清洗、价格清洗后的正式结果。

4.2.2 设计说明

旧结果层里已经形成了“标准化品牌、规范化规格、干净平台、干净价格、干净标题、干净规格、标题规范提示”等字段依赖；这些字段不能凭空消失，而应被正式吸收到清洗归一层。

4.2.3 字段设计
字段名 类型建议 必填 说明
id BIGINT PK 是 主键
raw_id BIGINT FK 是 对应 product_raw.id
standardized_brand VARCHAR(255)    否 标准化品牌
normalized_spec VARCHAR(255)    否 规范化规格
clean_platform VARCHAR(64)    否 干净平台
clean_price DECIMAL(10,2)    否 干净价格
clean_title VARCHAR(1000)    否 干净标题
clean_spec VARCHAR(255)    否 干净规格
normalize_note VARCHAR(500)    否 标题规范提示/清洗说明
product_name_normalized VARCHAR(255)    否 归一后的商品名
package_quantity DECIMAL(10,2)    否 包装数量
package_unit VARCHAR(32)    否 包装单位
spec_parse_status VARCHAR(32)    否 规格解析状态
clean_version VARCHAR(32)    是 清洗规则版本
created_at DATETIME 是 创建时间
updated_at DATETIME 是 更新时间
4.2.4 索引建议
idx_product_clean_raw_id (raw_id)
idx_product_clean_brand_spec_platform (standardized_brand, normalized_spec, clean_platform)
4.3 audit_result
4.3.1 表定位

审核结果表，承载异常判定事实与命中依据。

4.3.2 设计说明

这是 2 号窗口最关键的表。
后续 4 号窗口必须围绕它把“异常为什么成立”沉淀成系统事实，而不是只保留 yes/no 结果。总验收也要求每条异常至少能说明命中规则、规则版本、输入值、比较依据和最终原因。

4.3.3 设计承接的旧字段

旧 anomaly_details 里已有下列业务字段依赖：

显式低价阈值
组内均价
当前价格/组均价比
低价规则来源
异常原因

这些字段必须正式迁入该表。

4.3.4 字段设计
字段名 类型建议 必填 说明
id BIGINT PK 是 主键
clean_id BIGINT FK 是 对应 product_clean.id
anomaly_type VARCHAR(64)    是 异常类型，如 low_price / cross_platform_gap / spec_risk
is_hit BOOLEAN 是 是否命中
hit_rule_code VARCHAR(64)    否 命中规则编码
hit_rule_version VARCHAR(32)    否 命中规则版本
rule_definition_id BIGINT FK 否 指向 rule_definition.id
explicit_low_price_threshold DECIMAL(10,2)    否 显式低价阈值
group_avg_price DECIMAL(10,2)    否 组内均价
price_to_group_avg_ratio DECIMAL(10,4)    否 当前价格 / 组均价比
low_price_rule_source VARCHAR(64)    否 低价规则来源，如 explicit_rule / stat_rule / both
reason_text VARCHAR(1000)    否 异常原因
input_snapshot_json JSON 否 判定输入快照
result_status VARCHAR(32)    是 结果状态，如 pending_review / reviewed
audited_at DATETIME 否 判定时间
created_at DATETIME 是 创建时间
updated_at DATETIME 是 更新时间
4.3.5 索引建议
idx_audit_result_clean_id (clean_id)
idx_audit_result_anomaly_type_hit (anomaly_type, is_hit)
idx_audit_result_rule_definition_id (rule_definition_id)
idx_audit_result_audited_at (audited_at)
4.4 rule_definition
4.4.1 表定位

规则定义表，承载正式业务规则本体。

4.4.2 设计说明

该表解决的是“规则是什么”，支撑 4 号窗口的规则配置化、版本化和命中留痕。

4.4.3 字段设计
字段名 类型建议 必填 说明
id BIGINT PK 是 主键
rule_code VARCHAR(64)    是 规则编码
rule_name VARCHAR(255)    是 规则名称
rule_type VARCHAR(64)    是 规则类型，如 low_price / gap / spec_risk
business_domain VARCHAR(64)    否 所属业务域
version VARCHAR(32)    是 规则版本
enabled BOOLEAN 是 是否启用
threshold_config_json JSON 否 阈值配置
description TEXT 否 规则说明
source_doc_path VARCHAR(1000)    否 来源规则文档路径
effective_from DATETIME 否 生效开始时间
effective_to DATETIME 否 生效结束时间
created_at DATETIME 是 创建时间
updated_at DATETIME 是 更新时间
4.4.4 索引建议
唯一索引：uk_rule_definition_code_version (rule_code, version)
4.5 rule_chunk
4.5.1 表定位

规则文档切块表，承载规则解释系统的检索素材。

4.5.2 设计说明

该表服务于 5 号窗口的 RAG 规则解释能力，要求能追到具体文档、章节、chunk 和 metadata。总验收对此有明确要求。

4.5.3 字段设计
字段名 类型建议 必填 说明
id BIGINT PK 是 主键
rule_definition_id BIGINT FK 否 对应 rule_definition.id
doc_name VARCHAR(255)    是 文档名
section_title VARCHAR(255)    否 章节标题
chunk_index INT 是 chunk 序号
chunk_text TEXT 是 chunk 内容
metadata_json JSON 否 元数据
embedding_ref VARCHAR(255)    否 向量索引引用标识
is_active BOOLEAN 是 是否启用
created_at DATETIME 是 创建时间
4.5.4 索引建议
idx_rule_chunk_rule_definition_id (rule_definition_id)
唯一索引：uk_rule_chunk_rule_idx (rule_definition_id, chunk_index)
4.6 review_task
4.6.1 表定位

人工复核任务表，承载当前待办任务与状态流转对象。

4.6.2 设计说明

后续 7 号窗口会依赖这张表做异常列表、详情、处理归属、状态变更与导出。
“异常结果”和“复核任务”必须分层。

4.6.3 字段设计
字段名 类型建议 必填 说明
id BIGINT PK 是 主键
audit_result_id BIGINT FK 是 对应 audit_result.id
task_status VARCHAR(32)    是 任务状态，如 pending / processing / done
priority VARCHAR(16)    否 优先级
assigned_to VARCHAR(64)    否 分配对象
assigned_at DATETIME 否 分配时间
due_at DATETIME 否 截止时间
created_by VARCHAR(64)    否 创建人
created_at DATETIME 是 创建时间
updated_at DATETIME 是 更新时间
4.6.4 索引建议
idx_review_task_audit_result_id (audit_result_id)
idx_review_task_status_assigned (task_status, assigned_to)
4.7 review_record
4.7.1 表定位

人工复核动作记录表，承载每次复核动作的留痕。

4.7.2 设计说明

该表用于支撑“误报 / 确认异常 / 备注 / 留记录”等动作闭环。
任务表只管当前状态，记录表负责历史动作。

4.7.3 字段设计
字段名 类型建议 必填 说明
id BIGINT PK 是 主键
review_task_id BIGINT FK 是 对应 review_task.id
action_type VARCHAR(32)    是 动作类型
action_result VARCHAR(64)    否 动作结果
reviewer VARCHAR(64)    否 复核人
remark VARCHAR(1000)    否 备注
evidence_snapshot_json JSON 否 操作时依据快照
created_at DATETIME 是 创建时间
4.7.4 索引建议
idx_review_record_task_id (review_task_id)
idx_review_record_created_at (created_at)
4.8 ask_log
4.8.1 表定位

问答请求日志表，承载一次 /ask 主请求的整体输入输出。

4.8.2 设计说明

当前 app/schemas/ask.py 已经定义 ask 主响应字段为：

route
answer
tools_used
analysis_result
retrieval_result
explanation_result
trace

因此该表设计必须承接这组合同字段，而不是另造一套口径。

4.8.3 字段设计
字段名 类型建议 必填 说明
id BIGINT PK 是 主键
trace_id VARCHAR(64)    是 全链路追踪 ID
question VARCHAR(2000)    是 用户问题
route VARCHAR(32)    是 路由类型
answer_text TEXT 否 最终回答
tools_used_json JSON 否 工具列表
analysis_result_json JSON 否 数据分析结果
retrieval_result_json JSON 否 检索结果
explanation_result_json JSON 否 解释结果
trace_json JSON 否 工具调用链路
subject_audit_result_id BIGINT FK 否 关联审核结果
status VARCHAR(32)    是 请求状态
created_at DATETIME 是 创建时间
4.8.4 索引建议
idx_ask_log_trace_id (trace_id)
idx_ask_log_route (route)
idx_ask_log_created_at (created_at)
4.9 model_call_log
4.9.1 表定位

模型调用日志表，承载 ask 链路内部具体一次模型调用明细。

4.9.2 设计说明

该表用于支撑后续 trace、性能分析、调试审计。
ask_log 记录请求级别，model_call_log 记录步骤级别，粒度不能混。

4.9.3 字段设计
字段名 类型建议 必填 说明
id BIGINT PK 是 主键
ask_log_id BIGINT FK 是 对应 ask_log.id
trace_id VARCHAR(64)    是 trace_id
call_stage VARCHAR(64)    是 调用阶段
model_vendor VARCHAR(64)    否 模型提供方
model_name VARCHAR(128)    否 模型名称
request_payload_json JSON 否 请求载荷
response_payload_json JSON 否 响应载荷
prompt_tokens INT 否 输入 tokens
completion_tokens INT 否 输出 tokens
latency_ms INT 否 耗时毫秒
error_message VARCHAR(1000)    否 错误信息
created_at DATETIME 是 创建时间
4.9.4 索引建议
idx_model_call_log_ask_log_id (ask_log_id)
idx_model_call_log_trace_id (trace_id)
idx_model_call_log_call_stage (call_stage)

5. 旧字段到新表的映射关系

基于当前 legacy_sqlite.py 中的查询字段，正式映射建议如下：

旧字段 新表 新字段
标准化品牌 product_clean standardized_brand
规范化规格 product_clean normalized_spec
干净平台 product_clean clean_platform
干净价格 product_clean clean_price
干净标题 product_clean clean_title
干净规格 product_clean clean_spec
标题规范提示 product_clean normalize_note
显式低价阈值 audit_result explicit_low_price_threshold
组内均价 audit_result group_avg_price
当前价格/组均价比 audit_result price_to_group_avg_ratio
低价规则来源 audit_result low_price_rule_source
异常原因 audit_result reason_text

6. 当前表设计明确不做的内容

为了遵守 2 号窗口边界，本阶段明确不主写以下内容：

不正式实现规则判定逻辑
不正式实现 RAG 检索逻辑
不正式实现 /ask 编排逻辑
不正式实现人工复核页面
不正式实现错误码与统一响应体系
不正式实现 logger / exception 主体逻辑

这些属于 3～7 号窗口职责，2 号窗口只负责把数据承载对象定好。

7. 当前已识别风险
   7.1 旧 SQLite 路径仍有口径冲突

目录树显示旧库在 data/legacy/price_audit.db，但 legacy_sqlite.py 默认路径仍指向 data/price_audit.db。后续迁移文档必须明确以实际资产区路径为准。

7.2 app/models/ 目录尚未创建

当前 app/models/ 不存在，说明 ORM 层还没正式开始。这个问题必须在 2 号窗口后续代码产物中补上。

7.3 ask 接口层 schema 已先行，日志表不能另起炉灶

当前 AskResponse 字段合同已经稳定，ask_log 必须承接现有接口口径。

8. 下一步落地内容

本表设计文档确定后，2 号窗口下一步应继续产出：

docs/database/migration_plan.md
app/models/ 下正式 ORM 文件
app/schemas/audit.py
app/schemas/review.py
app/schemas/rule.py
app/schemas/log.py

9. 一句话总结

本表设计的核心结论是：

正式数据库将围绕“原始数据、清洗归一、审核结果、规则定义、规则解释素材、复核任务、复核记录、问答日志、模型调用日志”九张主干表展开，而不是继续围绕旧
SQLite 的阶段产物表组织。