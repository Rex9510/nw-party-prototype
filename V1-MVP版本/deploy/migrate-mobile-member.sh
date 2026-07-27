#!/usr/bin/env bash
set -e
DB=/var/www/nwparty/data/nwparty.db
echo "--- before ---"
sqlite3 "$DB" "PRAGMA table_info(members);" | tail -10
echo
echo "--- ALTER ---"
sqlite3 "$DB" "ALTER TABLE members ADD COLUMN is_mobile_member BOOLEAN DEFAULT 0;" 2>&1 || echo "is_mobile_member 已存在"
sqlite3 "$DB" "ALTER TABLE members ADD COLUMN flow_in_date DATE;" 2>&1 || echo "flow_in_date 已存在"
echo
echo "--- after ---"
sqlite3 "$DB" "PRAGMA table_info(members);" | tail -10
