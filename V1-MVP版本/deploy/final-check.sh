#!/usr/bin/env bash
echo "--- 1) 前端入口 ---"
curl -s -o /dev/null -w "status=%{http_code} size=%{size_download}\n" \
  http://47.107.77.15:8081/pages/members/new

echo
echo "--- 2) API 字段验证（直接打 8000）---"
TOKEN=$(curl -s -X POST http://47.107.77.15:8081/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -s "http://47.107.77.15:8081/api/v1/members?page_size=1" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('total:', d['total'])
if d['items']:
    keys = sorted(d['items'][0].keys())
    has_new = 'is_mobile_member' in keys and 'flow_in_date' in keys
    print('has new fields:', has_new)
    print('keys:', keys)
"

echo
echo "--- 3) nginx 代理 /api 也通 ---"
curl -s -o /dev/null -w "api status=%{http_code}\n" \
  http://47.107.77.15:8081/api/v1/members \
  -H "Authorization: Bearer $TOKEN"
