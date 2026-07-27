#!/usr/bin/env bash
set -e
echo "=== login ==="
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "TOKEN=${TOKEN:0:40}..."

echo
echo "=== list members (检查新字段在响应中) ==="
curl -s "http://127.0.0.1:8000/api/v1/members?page_size=2" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('total:', d.get('total'))
if d.get('items'):
    item = d['items'][0]
    print('item fields:', sorted(item.keys()))
    print('is_mobile_member:', item.get('is_mobile_member'))
    print('flow_in_date:', item.get('flow_in_date'))
    print('first item join_date:', item.get('join_date'))
"

echo
echo "=== 取 1 个党员详情 ==="
ID=$(curl -s "http://127.0.0.1:8000/api/v1/members?page_size=1" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json;print(json.load(sys.stdin)['items'][0]['id'])")
echo "id=$ID"
curl -s "http://127.0.0.1:8000/api/v1/members/$ID" -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('keys:', sorted(d.keys()))
print('is_mobile_member:', d.get('is_mobile_member'))
print('flow_in_date:', d.get('flow_in_date'))
"

echo
echo "=== 测试：is_mobile_member=true 但 flow_in_date=null 应该 422 ==="
curl -s -X POST http://127.0.0.1:8000/api/v1/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"测试流动党员失败",
    "phone":"13900000099",
    "gender":"male",
    "join_date":"2020-01-01",
    "branch_id":1,
    "roles":["party_member"],
    "is_mobile_member":true
  }' | python3 -m json.tool 2>&1 | head -20

echo
echo "=== 测试：is_mobile_member=true + flow_in_date 正常 ==="
curl -s -X POST http://127.0.0.1:8000/api/v1/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"测试流动党员",
    "phone":"13900000098",
    "gender":"male",
    "join_date":"2020-01-01",
    "branch_id":1,
    "roles":["party_member"],
    "is_mobile_member":true,
    "flow_in_date":"2024-06-15"
  }' | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('id:', d.get('id'))
print('name:', d.get('name'))
print('is_mobile_member:', d.get('is_mobile_member'))
print('flow_in_date:', d.get('flow_in_date'))
"
