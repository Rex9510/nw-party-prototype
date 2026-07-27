#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- users.branch_id=1 (会被孤儿清理删掉) ---"
sqlite3 -header -column "$DB" "SELECT id,phone,name,role,branch_id FROM users WHERE branch_id=1;"
echo
echo "--- 全部 users ---"
sqlite3 -header -column "$DB" "SELECT id,phone,name,role,branch_id,community_id FROM users;"
