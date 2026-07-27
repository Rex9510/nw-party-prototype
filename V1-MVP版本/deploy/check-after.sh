#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "members branch=1: $(sqlite3 "$DB" "SELECT COUNT(*) FROM members WHERE branch_id=1;")"
echo "users branch=1: $(sqlite3 "$DB" "SELECT COUNT(*) FROM users WHERE branch_id=1;")"
echo "study_hours 1,2,3: $(sqlite3 "$DB" "SELECT COUNT(*) FROM study_hours WHERE member_id IN (1,2,3);")"
echo "branches id=1: $(sqlite3 "$DB" "SELECT COUNT(*) FROM branches WHERE id=1;")"
echo
echo "--- 检查 member_imports ---"
sqlite3 -header -column "$DB" "SELECT * FROM member_imports;"
echo "--- 检查 activities ---"
sqlite3 -header -column "$DB" "SELECT id, theme, branch_id, created_by FROM activities;"
echo "--- 检查 audit_flows / audit_logs ---"
sqlite3 -header -column "$DB" "SELECT * FROM audit_flows;"
sqlite3 -header -column "$DB" "SELECT * FROM audit_logs;"
