#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
sqlite3 -header -column "$DB" "SELECT id, theme, status FROM activities ORDER BY id DESC LIMIT 3;"
echo
echo "--- activity_participants 最近 5 行 ---"
sqlite3 -header -column "$DB" "SELECT id, activity_id, member_id, study_hours FROM activity_participants ORDER BY id DESC LIMIT 5;"
