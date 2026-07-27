-- 2026-07-26: 流动党员 + 流入日期
-- 因为 init_db.py 用 Base.metadata.create_all，不会 ALTER 现有表
-- 上线前手动跑一次（幂等：列已存在时忽略错误）

ALTER TABLE members ADD COLUMN is_mobile_member BOOLEAN DEFAULT 0;
ALTER TABLE members ADD COLUMN flow_in_date DATE;
