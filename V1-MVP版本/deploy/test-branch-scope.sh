#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db

# 用 python 算 pass1234 的 bcrypt 哈希
HASH=$(/var/www/nwparty/venv/bin/python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt'], deprecated='auto').hash('pass1234'))")
echo "hash: $HASH"

echo
echo "--- 1) 当前 activities ---"
sqlite3 -header -column "$DB" "SELECT id, theme, organizer_branch_id, community_id, status FROM activities;"

echo
echo "--- 2) 陈书记 (id=4) 当前状态 ---"
sqlite3 -header -column "$DB" "SELECT id, phone, name, role, branch_id, password_hash IS NOT NULL AS has_pwd FROM users WHERE id=4;"

echo
echo "--- 3) 临时：陈书记 role 已是 branch_secretary（如果没设就设）; 重置密码为 pass1234 ---"
sqlite3 "$DB" "UPDATE users SET role='branch_secretary' WHERE id=4 AND role!='branch_secretary';"
sqlite3 "$DB" "UPDATE users SET password_hash='$HASH' WHERE id=4;"
sqlite3 -header -column "$DB" "SELECT id, phone, name, role, branch_id FROM users WHERE id=4;"

echo
echo "--- 4) A: 陈书记在 branch=1 (自己支部) → 应看到 0 场（活动都在 branch=5）---"
sqlite3 "$DB" "UPDATE users SET branch_id=1 WHERE id=4;"
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000003","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
echo "TOKEN=${TOKEN:0:30}..."
curl -s "http://127.0.0.1:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo
curl -s "http://127.0.0.1:8000/api/v1/stats/stats?period=year&year=2026" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('label:', d.get('label'))
for it in d.get('items', []):
    print(f\"  {it['label']}: {it['session_count']} 场, {it['participant_count']} 人\")
"

echo
echo "--- 5) B: 陈书记挪到 branch=5 → 应看到 1 场 ---"
sqlite3 "$DB" "UPDATE users SET branch_id=5 WHERE id=4;"
curl -s "http://127.0.0.1:8000/api/v1/stats/stats?period=year&year=2026" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('label:', d.get('label'))
for it in d.get('items', []):
    print(f\"  {it['label']}: {it['session_count']} 场, {it['participant_count']} 人\")
"

echo
echo "--- 6) 恢复陈书记原样 ---"
sqlite3 "$DB" "UPDATE users SET branch_id=1 WHERE id=4;"
