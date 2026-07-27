#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 哪些 activities 引用 branch=1 ---"
sqlite3 -header -column "$DB" "SELECT id, theme FROM activities WHERE id IN (SELECT id FROM activities);"
echo
echo "--- activities 表结构 ---"
sqlite3 "$DB" "SELECT sql FROM sqlite_master WHERE name='activities';"
