#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db

echo "--- 0) 当前 state ---"
echo "[members branch=1]"
sqlite3 -header -column "$DB" "SELECT id,name,phone,status FROM members WHERE branch_id=1;"
echo "[users branch=1]"
sqlite3 -header -column "$DB" "SELECT id,phone,name,role FROM users WHERE branch_id=1;"

echo
echo "--- 1) 删支部 1（API 调） ---"
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
HTTP=$(curl -s -o /tmp/resp -w '%{http_code}' -X DELETE \
  "http://127.0.0.1:8000/api/v1/orgs/branches/1" \
  -H "Authorization: Bearer $TOKEN")
echo "HTTP=$HTTP"
echo "body=$(cat /tmp/resp)"

echo
echo "--- 2) 验证结果 ---"
echo "[branches]"
sqlite3 -header -column "$DB" "SELECT id,name FROM branches;"
echo
echo "[members]"
sqlite3 -header -column "$DB" "SELECT id,name,phone,status,branch_id FROM members;"
echo
echo "[users]"
sqlite3 -header -column "$DB" "SELECT id,phone,name,role,branch_id FROM users;"
echo
echo "[activity_participants member_id IN (1,2,3)]"
sqlite3 -header -column "$DB" "SELECT * FROM activity_participants WHERE member_id IN (1,2,3);"
echo
echo "[study_hours member_id IN (1,2,3)]"
sqlite3 -header -column "$DB" "SELECT * FROM study_hours WHERE member_id IN (1,2,3);"
