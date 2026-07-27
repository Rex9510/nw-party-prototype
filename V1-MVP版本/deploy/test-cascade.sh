#!/usr/bin/env bash
set -e
DB=/var/www/nwparty/data/nwparty.db

echo "--- 0) 当前 state ---"
sqlite3 -header -column "$DB" "SELECT id,name,phone,status,branch_id FROM members;"

echo
echo "--- 1) 把 3 人转 dimission（你之前是从前台操作让他们 dimission 了，这里复现）---"
sqlite3 "$DB" "UPDATE members SET status='dimission' WHERE id IN (1,2,3);"
sqlite3 -header -column "$DB" "SELECT id,name,phone,status FROM members WHERE id IN (1,2,3);"

echo
echo "--- 2) 删支部 1 ---"
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
echo "--- 3) 验证：3 个 dimission 党员连带 user 一起没了 ---"
echo "members:"
sqlite3 -header -column "$DB" "SELECT id,name,phone,status,branch_id FROM members;"
echo
echo "users (139 开头):"
sqlite3 -header -column "$DB" "SELECT id,phone,name,role FROM users WHERE phone LIKE '139%';"
echo
echo "branches:"
sqlite3 -header -column "$DB" "SELECT id,name FROM branches;"
