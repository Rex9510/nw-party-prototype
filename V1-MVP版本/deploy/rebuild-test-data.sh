#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 重建南岭社区第一党支部 + 测试数据（你之前测 API 用）---"
sqlite3 "$DB" "INSERT INTO branches (id, community_id, name) VALUES (1, 1, '南岭社区第一党支部');"
sqlite3 "$DB" "INSERT INTO members (id, branch_id, name, phone, status, is_mobile_member) VALUES (1, 1, '张三', '13900000001', 'dimission', 0);"
sqlite3 "$DB" "INSERT INTO members (id, branch_id, name, phone, status, is_mobile_member) VALUES (2, 1, '李四', '13900000002', 'dimission', 0);"
sqlite3 "$DB" "INSERT INTO members (id, branch_id, name, phone, status, is_mobile_member) VALUES (3, 1, '王五', '13900000003', 'dimission', 0);"
sqlite3 "$DB" "INSERT INTO users (phone, password_hash, name, role, branch_id, community_id, status) VALUES ('13800000003', 'x', '陈书记（支部）', 'branch_secretary', 1, 1, 'active');"
sqlite3 "$DB" "INSERT INTO users (phone, password_hash, name, role, branch_id, community_id, status) VALUES ('13800000010', 'x', '张三（党员）', 'member', 1, 1, 'active');"
sqlite3 "$DB" "INSERT INTO study_hours (member_id, year, total_hours, activity_count) VALUES (1, 2026, 8, 2);"
sqlite3 "$DB" "INSERT INTO study_hours (member_id, year, total_hours, activity_count) VALUES (2, 2026, 4, 1);"
echo "done"
echo
echo "--- state ---"
sqlite3 -header -column "$DB" "SELECT id,name FROM branches WHERE id=1;"
sqlite3 -header -column "$DB" "SELECT id,name,status,branch_id FROM members WHERE branch_id=1;"
sqlite3 -header -column "$DB" "SELECT id,phone,name,role,branch_id FROM users WHERE branch_id=1;"
sqlite3 -header -column "$DB" "SELECT * FROM study_hours WHERE member_id IN (1,2);"
