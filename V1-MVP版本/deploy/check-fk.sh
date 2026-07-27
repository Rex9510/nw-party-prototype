#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 1) 所有引用 members.id 的外键 ---"
sqlite3 -header -column "$DB" "
SELECT m.name AS from_table, p.'from' AS col, fk.'table' AS ref_table, fk.'to' AS ref_col
FROM pragma_foreign_key_list('members') fk
JOIN sqlite_master m ON m.name = fk.'table';
"
echo
echo "--- 2) 当前所有表 ---"
sqlite3 "$DB" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
echo
echo "--- 3) 哪些表的 sql 引用了 members.id ---"
sqlite3 "$DB" "SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%members.id%' ORDER BY name;"
