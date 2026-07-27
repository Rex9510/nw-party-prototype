-- 手动迁移：给 members 表加 roles 和 identities 列
-- 如果项目当前用 PostgreSQL，请在 psql 里执行：
--   psql -U nwparty -d nwparty -f alembic_add_columns.sql

ALTER TABLE members ADD COLUMN IF NOT EXISTS roles JSON;
ALTER TABLE members ADD COLUMN IF NOT EXISTS identities JSON;
