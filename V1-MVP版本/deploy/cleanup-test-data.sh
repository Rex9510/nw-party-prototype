#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- before ---"
sqlite3 "$DB" "SELECT id,name,phone,is_mobile_member,flow_in_date FROM members;"

echo
echo "--- cleanup test data ---"
sqlite3 "$DB" "DELETE FROM users WHERE phone IN ('13900000099','13900000098');"
sqlite3 "$DB" "DELETE FROM members WHERE phone IN ('13900000099','13900000098');"

echo
echo "--- after ---"
sqlite3 "$DB" "SELECT id,name,phone,is_mobile_member,flow_in_date FROM members;"
