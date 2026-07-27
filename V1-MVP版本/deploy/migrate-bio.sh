#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- ALTER ---"
sqlite3 "$DB" "ALTER TABLE activities ADD COLUMN lecturer_bio TEXT;" 2>&1 || echo "(列已存在)"
echo
echo "--- table_info ---"
sqlite3 -header -column "$DB" "PRAGMA table_info(activities);" | grep -E "name|lecturer"
