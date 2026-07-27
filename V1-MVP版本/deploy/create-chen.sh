#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db

# 1) 算 pass1234 的 bcrypt 哈希
HASH=$(/var/www/nwparty/venv/bin/python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt'], deprecated='auto').hash('pass1234'))")
echo "hash: $HASH"

# 2) 找厦村社区下的支部
echo
echo "--- 厦村社区下的支部 ---"
sqlite3 -header -column "$DB" "SELECT id, name, community_id FROM branches WHERE community_id=3;"

# 3) 把 id=7 的朱启宝（system_admin）腾出来给陈书记？更安全的是建新行
#    users id=8 留给陈书记，role=branch_secretary
#    默认放"厦村社区工作站党支部" (id=5)
TARGET_BRANCH=5
echo
echo "--- 创建陈书记（id=8, phone=13800000003, role=branch_secretary, branch_id=$TARGET_BRANCH）---"
sqlite3 "$DB" "
INSERT OR REPLACE INTO users (id, phone, password_hash, name, role, street_id, community_id, branch_id, status)
VALUES (8, '13800000003', '$HASH', '陈书记（支部）', 'branch_secretary', 1, 3, $TARGET_BRANCH, 'active');
"
sqlite3 -header -column "$DB" "SELECT id, phone, name, role, branch_id, community_id FROM users WHERE id=8;"

echo
echo "--- 测试登录 ---"
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000003","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
echo "TOKEN=${TOKEN:0:30}..."

echo
echo "--- /me ---"
curl -s "http://127.0.0.1:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo
echo "--- 陈书记查 stats（应只看到自己支部的 1 场）---"
curl -s "http://127.0.0.1:8000/api/v1/stats/stats?period=year&year=2026" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('label:', d.get('label'))
for it in d.get('items', []):
    print(f\"  {it['label']}: {it['session_count']} 场, {it['participant_count']} 人\")
"
