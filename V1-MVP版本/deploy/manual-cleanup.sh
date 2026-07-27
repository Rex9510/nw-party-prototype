#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 启用 FK + 列出现状 ---"
sqlite3 "$DB" "PRAGMA foreign_keys = ON;"
echo
echo "1) study_hours member IN (1,2,3):"
sqlite3 "$DB" "SELECT id, member_id FROM study_hours WHERE member_id IN (1,2,3);"
echo
echo "2) 删 study_hours 引用 1,2"
sqlite3 "$DB" "DELETE FROM study_hours WHERE member_id IN (1,2,3);"
echo "rows after: $(sqlite3 "$DB" "SELECT COUNT(*) FROM study_hours WHERE member_id IN (1,2,3);")"
echo
echo "3) 删 users branch_id=1"
sqlite3 "$DB" "DELETE FROM users WHERE branch_id=1;"
echo "rows after: $(sqlite3 "$DB" "SELECT COUNT(*) FROM users WHERE branch_id=1;")"
echo
echo "4) 删 members branch_id=1"
sqlite3 "$DB" "DELETE FROM members WHERE branch_id=1;"
echo "rows after: $(sqlite3 "$DB" "SELECT COUNT(*) FROM members WHERE branch_id=1;")"
echo
echo "5) 删 branch 1"
sqlite3 "$DB" "DELETE FROM branches WHERE id=1;"
echo "rows after: $(sqlite3 "$DB" "SELECT COUNT(*) FROM branches WHERE id=1;")"
echo
echo "--- 终态 ---"
sqlite3 -header -column "$DB" "SELECT id,name FROM branches;"
sqlite3 -header -column "$DB" "SELECT id,name,phone,status,branch_id FROM members;"
sqlite3 -header -column "$DB" "SELECT id,phone,name,role,branch_id FROM users;"
