#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 哪些表 FK 引用 communities ---"
sqlite3 "$DB" "SELECT DISTINCT m.name FROM sqlite_master m, pragma_foreign_key_list(m.name) fk WHERE fk.'table'='communities';"
echo
for tbl in branches activities users members; do
  echo "--- $tbl 中 community_id=1 的行 ---"
  sqlite3 -header -column "$DB" "SELECT id, name, community_id FROM $tbl WHERE community_id=1;"
done
echo
echo "--- users 中 community_id=1 ---"
sqlite3 -header -column "$DB" "SELECT id, phone, name, role, community_id, branch_id FROM users WHERE community_id=1;"
