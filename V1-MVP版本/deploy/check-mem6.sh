#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- member_id=6 是否存在 ---"
sqlite3 -header -column "$DB" "SELECT id, name, phone, status, branch_id FROM members WHERE id=6;"
echo
echo "--- 所有 member ---"
sqlite3 -header -column "$DB" "SELECT id, name, status FROM members;"
