#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "[communities]"
sqlite3 -header -column "$DB" "SELECT id,name,street_id FROM communities;"
echo
echo "[branches]"
sqlite3 -header -column "$DB" "SELECT id,name,community_id FROM branches;"
echo
echo "[users]"
sqlite3 -header -column "$DB" "SELECT id,phone,name,role,community_id,branch_id FROM users;"
