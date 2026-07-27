#!/usr/bin/env bash
echo "=== 测试 1: photo_urls 传 2 张 -> 应被 422 ==="
TOKEN=$(curl -s -X POST http://47.107.77.15:8081/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -s -X POST http://47.107.77.15:8081/api/v1/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"测试照片上限",
    "phone":"13911110000",
    "gender":"male",
    "join_date":"2020-01-01",
    "branch_id":1,
    "roles":["party_member"],
    "photo_urls":["data:image/png;base64,AAAA","data:image/png;base64,BBBB"]
  }' | python3 -m json.tool 2>&1 | head -20

echo
echo "=== 测试 2: photo_urls 传 1 张 -> 应成功 ==="
curl -s -X POST http://47.107.77.15:8081/api/v1/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"测试1张照片",
    "phone":"13922220000",
    "gender":"male",
    "join_date":"2020-01-01",
    "branch_id":1,
    "roles":["party_member"],
    "photo_urls":["data:image/png;base64,AAAA"]
  }' | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('id:', d.get('id'), 'name:', d.get('name'), 'photo count:', len(d.get('photo_urls', [])))
"

echo
echo "=== 清理测试数据 ==="
DB=/var/www/nwparty/data/nwparty.db
sqlite3 "$DB" "DELETE FROM users WHERE phone IN ('13911110000','13922220000'); DELETE FROM members WHERE phone IN ('13911110000','13922220000');"
echo "ok"
