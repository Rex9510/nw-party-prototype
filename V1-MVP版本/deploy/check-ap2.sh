#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
sqlite3 -header -column "$DB" "SELECT * FROM activity_participants;"
echo
echo "--- 哪些表 FK 引用 members ---"
sqlite3 "$DB" "SELECT DISTINCT m.name FROM sqlite_master m, pragma_foreign_key_list(m.name) fk WHERE fk.'table'='members';"
echo
echo "--- 哪些表 FK 引用 branches ---"
sqlite3 "$DB" "SELECT DISTINCT m.name FROM sqlite_master m, pragma_foreign_key_list(m.name) fk WHERE fk.'table'='branches';"
