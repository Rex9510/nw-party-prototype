#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 哪些活动 organizer_branch_id=1 ---"
sqlite3 -header -column "$DB" "SELECT id, theme, organizer_branch_id FROM activities WHERE organizer_branch_id=1;"
