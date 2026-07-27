#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- state before ---"
sqlite3 -header -column "$DB" "SELECT id,name FROM branches;"
sqlite3 -header -column "$DB" "SELECT id,name,status,branch_id FROM members;"
sqlite3 -header -column "$DB" "SELECT id,phone,name,role,branch_id FROM users;"

echo
echo "--- DELETE branch 1 ---"
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
HTTP=$(curl -s -o /tmp/resp -w '%{http_code}' -X DELETE \
  'http://127.0.0.1:8000/api/v1/orgs/branches/1' \
  -H "Authorization: Bearer $TOKEN")
echo "HTTP=$HTTP body=$(cat /tmp/resp)"

echo
echo "--- after ---"
echo "[branches]"
sqlite3 -header -column "$DB" "SELECT id,name FROM branches;"
echo "[members]"
sqlite3 -header -column "$DB" "SELECT id,name,status,branch_id FROM members;"
echo "[users]"
sqlite3 -header -column "$DB" "SELECT id,phone,name,role,branch_id FROM users;"
echo "[study_hours]"
sqlite3 "$DB" "SELECT * FROM study_hours;"
echo "[activity_participants]"
sqlite3 "$DB" "SELECT * FROM activity_participants;"
