#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
sqlite3 -header -column "$DB" "SELECT id,name,status,branch_id FROM members WHERE branch_id=1;"
echo
sqlite3 -header -column "$DB" "SELECT id,phone,name,role,branch_id FROM users WHERE branch_id=1;"
