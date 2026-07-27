#!/usr/bin/env bash
echo "--- 登录 + 删社区 1 ---"
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
HTTP=$(curl -s -o /tmp/resp -w '%{http_code}' -X DELETE \
  'http://127.0.0.1:8000/api/v1/orgs/communities/1' \
  -H "Authorization: Bearer $TOKEN")
echo "HTTP=$HTTP"
echo "body=$(cat /tmp/resp)"
