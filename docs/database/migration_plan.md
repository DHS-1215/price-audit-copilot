数据库迁移方案（2号窗口正式版）

1. 文档目的

本文档用于明确鸿茅药酒电商维价审核 Copilot 在 2号窗口：数据库与数据模型阶段 的数据库迁移方向、迁移顺序、落地边界与风险控制方案。

本阶段不是把旧 SQLite 粗暴翻译成 MySQL，也不是顺手把 4～7 号窗口内容一起写了，而是要把：

正式数据库目标定清楚
旧原型数据来源定清楚
迁移顺序定清楚
Alembic 的使用方式定清楚
哪些先迁、哪些后迁、哪些不迁定清楚

2. 当前现状

结合 1 号窗口交接和当前仓库结构，现状已经比较明确：

2.1 工程落点已具备

当前仓库已经有：

docs/database/
alembic/
app/schemas/
app/repositories/
data/legacy/price_audit.db

这意味着 2 号窗口不需要再讨论“数据库内容放哪”，而是可以直接进入正式数据模型与迁移设计。

2.2 旧数据底盘仍是 SQLite 兼容层

当前旧系统依赖 app/repositories/legacy_sqlite.py，其职责本质上是：

CSV 阶段结果落库
原型查询辅助
支撑第二周结果层与后续早期问答验证

它不是未来正式主库实现。

2.3 旧 SQLite 路径口径存在漂移

当前仓库实际旧库位于：

data/legacy/price_audit.db

但 legacy_sqlite.py 默认路径函数仍返回：

data/price_audit.db

所以迁移文档必须明确：后续统一以资产区实际落点为准，即 data/legacy/price_audit.db 作为旧库迁移来源。

2.4 当前 ORM 层尚未开始

目前 app/models/ 目录还不存在。
这说明迁移计划必须从“先建正式模型和迁移骨架”开始，不能跳到“导历史数据”那一步。

3. 迁移目标

本次数据库迁移的目标，不是“把 SQLite 换成 MySQL”这么肤浅，而是把项目从原型数据承载方式升级为正式数据底盘，以支撑后续：

4 号窗口：规则引擎与结果层
5 号窗口：RAG 检索与规则解释
6 号窗口：统一问答编排
7 号窗口：人工复核闭环
8 号窗口：测试、部署与交付

正式目标数据库应能承载以下九类对象：

product_raw
product_clean
audit_result
rule_definition
rule_chunk
review_task
review_record
ask_log
model_call_log

4. 迁移总体原则
   4.1 先建正式模型，再考虑迁历史数据

顺序必须是：

先完成 ER 设计
再完成表结构设计
再落 app/models/
再初始化 Alembic
再生成正式迁移脚本
最后再考虑把旧 SQLite 的关键数据导入新库

不能反过来。

因为 2 号窗口的职责是业务建模，不是“先把旧数据搬过去再说”。这点在 1 号窗口交接里已经强调过：不要把 SQLite 直接翻译成 MySQL。

4.2 只迁有业务价值的数据，不迁原型垃圾

旧 SQLite 里当前主要是：

cleaned_products
normalized_products
anomaly_details
pipeline_runs

这些表中，真正有正式迁移价值的是：

清洗归一结果相关字段
异常结果层相关字段

而像 pipeline_runs 这种原型阶段轻量元数据表，本期不作为正式核心迁移对象。

4.3 迁移必须尊重现有结果层事实

正式库必须承接旧系统已经形成的关键字段口径，例如：

标准化品牌
规范化规格
干净平台
干净价格
显式低价阈值
组内均价
当前价格/组均价比
低价规则来源
异常原因

这些字段不能迁着迁着就改名改到亲妈都认不出。

4.4 先跑通正式结构，再追求历史完整性

你现在这个阶段最重要的是让后续窗口有正式数据底盘，而不是先花大量精力做“历史全量迁移完美工程”。
因此本期推荐策略是：

先结构迁移
再做最小必要历史导入
最后在后续窗口逐步替换旧 SQLite 依赖

这才务实，不然容易把 2 号窗口拖成泥潭。

5. 迁移范围
   5.1 本期必须完成的迁移范围
   A. 正式结构迁移

必须完成：

正式表设计
ORM 模型建立
Alembic 初始化
首批 migration 脚本生成
B. 基础规则定义初始化

必须考虑：

rule_definition 的初始化插入方案
rule_chunk 的后续导入预留
C. 旧结果层字段映射方案

必须形成：

旧字段 → 新表字段映射关系
旧表 → 新实体层次映射关系
5.2 本期建议完成，但可分步实现的内容
A. 旧 SQLite 中关键结果数据的最小导入

建议至少预留：

从 anomaly_details 导入到 product_clean + audit_result
必要时从 cleaned_products / normalized_products 补充清洗层字段
B. 种子数据脚本

例如：

基础规则定义 seed
基础状态枚举初始化说明
5.3 本期明确不做的内容

为了守住 2 号窗口边界，本期明确不主写：

不正式做规则判定服务
不正式做 RAG ingest / retriever 逻辑
不正式做 ask 编排
不正式做 review 页面和导出逻辑
不正式做统一 logger / exception / response 体系

6. 迁移阶段拆分

推荐把数据库迁移分成 4 个阶段推进。

6.1 第一阶段：建立正式模型骨架
目标

先把正式数据库对象定义清楚，让 ORM 层和迁移体系有落点。

本阶段应完成
创建 app/models/
建立基础模型文件：
base.py
product_raw.py
product_clean.py
audit_result.py
rule_definition.py
rule_chunk.py
review_task.py
review_record.py
ask_log.py
model_call_log.py
保证模型命名、字段命名、主外键关系与表设计文档一致
本阶段结果

达到“正式数据库对象已经有代码承载”的状态，而不是继续只有文档没有模型。

6.2 第二阶段：初始化 Alembic 迁移体系
目标

把迁移从“手工改表”升级为正式版本化迁移。

本阶段应完成
初始化 Alembic 环境
配置数据库连接
让 Alembic 能读取 SQLAlchemy metadata
建立首批 migration 版本脚本
迁移版本建议

推荐按下面顺序拆分 migration：

0001_init_product_and_rule_tables

创建：

product_raw
product_clean
rule_definition
rule_chunk
0002_init_audit_tables

创建：

audit_result
0003_init_review_tables

创建：

review_task
review_record
0004_init_log_tables

创建：

ask_log
model_call_log
0005_seed_rule_definitions

插入：

基础规则定义数据
为什么这么拆

因为这能和后续窗口依赖顺序对上：

4 号窗口先依赖产品层 + 审核层
5 号窗口依赖规则层
6 号窗口依赖问答日志层
7 号窗口依赖复核层
6.3 第三阶段：建立旧数据映射与导入脚本
目标

把旧 SQLite 里的关键结果层数据，按正式结构导入新库。

数据来源

统一以：

data/legacy/price_audit.db

作为旧库来源。

导入策略

建议采用“脚本导入”，而不是在 migration 脚本里塞复杂数据转换逻辑。

原因

Alembic migration 适合做：

建表
改字段
初始化少量 seed

不适合做大量脏数据转换。
脏数据转换应该交给单独脚本，例如：

scripts/migrate_legacy_sqlite.py
旧表映射建议
cleaned_products

优先映射到：

product_raw
product_clean
normalized_products

优先映射到：

product_clean
anomaly_details

拆分映射到：

product_clean
audit_result
pipeline_runs

本期不作为正式迁移核心对象，可忽略或只保留参考。

导入原则
不追求一次性导全部历史
先导关键样本和关键结果层
先保证字段映射正确，再考虑批量导入
6.4 第四阶段：切换正式数据底盘
目标

逐步让后续窗口不再继续依赖 legacy_sqlite.py 作为主承载层。

切换方式

建议采用“保留兼容、逐步替换”的方式：

2 号窗口保留 legacy_sqlite.py 不删
4 号窗口开始优先写正式 audit_result
5 号窗口开始优先依赖正式规则表结构
6 号窗口开始优先写正式 ask_log / model_call_log
7 号窗口开始优先写正式 review_task / review_record
为什么不建议一次性删旧库

因为当前项目仍有旧主链可跑，1 号窗口交接已经明确采用了“收编 + 兼容”策略。一下子全推翻，很容易把链路打断。

7. 旧字段迁移规则

基于当前 legacy_sqlite.py，旧结果层字段迁移建议如下：

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

8. 技术实现建议
   8.1 数据库技术口径

根据总要求与 2 号窗口职责，本期正式数据库目标应统一为：

MySQL 8.0
SQLAlchemy 2.x
Alembic
8.2 兼容开发建议

考虑到你当前本地开发已经有 SQLite 原型资产，推荐开发上分成两层：

正式目标：MySQL 8.0
过渡参考：SQLite legacy 数据源

别反过来把 SQLite 当正式目标，那就跑偏了。

8.3 导入脚本建议

建议新增脚本：

scripts/migrate_legacy_sqlite.py

职责：

读取 data/legacy/price_audit.db
读取旧表
做字段映射
写入正式库

而不是把导入逻辑写进 legacy_sqlite.py 里继续养肥兼容层。

9. 风险与注意事项
   9.1 最大风险：把旧 SQLite 直接等同于正式数据库

这是最容易偷懒、也最容易把后面坑惨的方案。
2 号窗口要做的是业务建模，不是数据库方言替换。

9.2 第二个风险：先导数据，后补模型

顺序反了会非常恶心。
应该先：

定文档
定模型
定迁移
再导数据
9.3 第三个风险：兼容层继续写厚

legacy_sqlite.py 现在有价值，但它的定位是兼容层。
不能因为现在还能跑，就让它继续长成正式主库实现。

9.4 第四个风险：迁移范围失控

2 号窗口最怕顺手把规则引擎、RAG、ask 编排、review 状态流全写了。
那不是高效，那是串台。

10. 本阶段验收标准

本迁移方案落地后，2 号窗口至少应达到：

已有正式数据库迁移路线，不再停留在口头说明
app/models/ 已建立
Alembic 已可初始化并读取正式模型
首批 migration 拆分顺序清楚
旧 SQLite 到正式表的映射关系清楚
明确哪些数据迁、哪些不迁、哪些后迁
后续 4～7 号窗口都知道该往哪张正式表落

11. 一句话总结

本迁移方案的核心结论是：

本项目数据库升级采用“先正式建模与迁移、再按映射导入关键旧数据、最后逐步替换 SQLite 兼容层”的路线，而不是把旧 SQLite 直接翻译成
MySQL。