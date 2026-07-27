#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- before ---"
sqlite3 -header -column "$DB" "SELECT id, name, phone, status FROM members WHERE id IN (1,2,3);"
echo
echo "--- UPDATE ---"
sqlite3 "$DB" "UPDATE members SET status='active' WHERE id IN (1,2,3);"
echo "--- after ---"
sqlite3 -header -column "$DB" "SELECT id, name, phone, status FROM members WHERE id IN (1,2,3);"
