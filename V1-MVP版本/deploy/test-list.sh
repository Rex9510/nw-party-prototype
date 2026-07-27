#!/usr/bin/env bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
curl -s -o /dev/null -w 'status=%{http_code}\n' "http://127.0.0.1:8000/api/v1/activities?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
