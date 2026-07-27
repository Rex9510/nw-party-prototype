#!/usr/bin/env bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
echo "--- /activities/13 完整返回 ---"
curl -s "http://127.0.0.1:8000/api/v1/activities/13" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
