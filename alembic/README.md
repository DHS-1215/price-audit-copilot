# Alembic 迁移目录说明

本目录由 2 号窗口：数据库与数据模型窗口正式接手。

当前设计原则：

1. Alembic 负责正式表结构版本化迁移
2. 复杂旧 SQLite 数据转换不写进 migration，放到独立脚本处理
3. 数据库连接先使用 DATABASE_URL 环境变量或 alembic.ini 中的 sqlalchemy.url
4. 统一以 app.models.Base.metadata 作为 target_metadata

注意：
- 本目录初始化属于 2 号窗口职责
- 统一 config / logger / trace / exception 体系属于 3 号窗口职责
- 不要把脏数据清洗逻辑塞进 migration