#!/usr/bin/env bash
# 验证：现在 3 个人 active 时挡删，全 dimission 时放行
DB=/var/www/nwparty/data/nwparty.db
TOKEN=$(curl -s -X POST http://47.107.77.15:8081/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "--- 当前状态 ---"
sqlite3 -header -column "$DB" "SELECT id, name, status FROM members WHERE branch_id=1;"

echo
echo "--- 场景 A: 3 人全 active → 删支部应被 400 拦 ---"
curl -s -o /tmp/resp.json -w "status=%{http_code}\n" -X DELETE \
  "http://47.107.77.15:8081/api/v1/orgs/branches/1" \
  -H "Authorization: Bearer $TOKEN"
cat /tmp/resp.json | python3 -m json.tool 2>/dev/null

echo
echo "--- 场景 B: 把 3 人全转 dimission → 删支部应成功 ---"
sqlite3 "$DB" "UPDATE members SET status='dimission' WHERE id IN (1,2,3);"
curl -s -o /tmp/resp.json -w "status=%{http_code}\n" -X DELETE \
  "http://47.107.77.15:8081/api/v1/orgs/branches/1" \
  -H "Authorization: Bearer $TOKEN"
cat /tmp/resp.json 2>/dev/null

echo
echo "--- 场景 C: 验证后端响应了 200/204，支部已被删 ---"
sqlite3 -header -column "$DB" "SELECT id, name FROM branches;"

echo
echo "--- 恢复 3 人 active + 重建支部，方便你继续测 ---"
sqlite3 "$DB" "UPDATE members SET status='active' WHERE id IN (1,2,3);"
# 重建南岭社区第一党支部
sqlite3 "$DB" "INSERT INTO branches (id, community_id, name) VALUES (1, 1, '南岭社区第一党支部');"
# members 的 branch_id 不用动（删支部时 SQL 没 cascade，但重建后 ID 1 跟原来一样，关系还在）
sqlite3 -header -column "$DB" "SELECT id, name, status, branch_id FROM members WHERE branch_id=1;"
echo "branches:"
sqlite3 -header -column "$DB" "SELECT id, name FROM branches;"
