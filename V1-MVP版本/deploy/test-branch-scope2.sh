#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db

# 算 pass1234 的 bcrypt
HASH=$(/var/www/nwparty/venv/bin/python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt'], deprecated='auto').hash('pass1234'))")
echo "hash: $HASH"

echo
echo "--- 1) 把刘海宝（id=6, 在 branch=5）临时改成 branch_secretary + 重置密码 ---"
sqlite3 "$DB" "UPDATE users SET role='branch_secretary', password_hash='$HASH' WHERE id=6;"
sqlite3 -header -column "$DB" "SELECT id, phone, name, role, branch_id FROM users WHERE id=6;"

echo
echo "--- 2) 刘海宝 (18126323580) 登录 ---"
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"18126323580","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
echo "TOKEN=${TOKEN:0:30}..."

echo
echo "--- 3) /me 看 scope 字段 ---"
curl -s "http://127.0.0.1:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo
echo "--- 4) A: 在 branch=5 (厦村社区工作站党支部) → 应看到 1 场（活动在 branch=5）---"
curl -s "http://127.0.0.1:8000/api/v1/stats/stats?period=year&year=2026" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('label:', d.get('label'))
for it in d.get('items', []):
    print(f\"  {it['label']}: {it['session_count']} 场, {it['participant_count']} 人\")
"

echo
echo "--- 5) B: 挪到 branch=6 (厦村股份合作公司党支部) → 应看到 0 场 ---"
sqlite3 "$DB" "UPDATE users SET branch_id=6 WHERE id=6;"
curl -s "http://127.0.0.1:8000/api/v1/stats/stats?period=year&year=2026" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('label:', d.get('label'))
for it in d.get('items', []):
    print(f\"  {it['label']}: {it['session_count']} 场, {it['participant_count']} 人\")
"

echo
echo "--- 6) 恢复刘海宝原状 ---"
sqlite3 "$DB" "UPDATE users SET role='street_lead', branch_id=5 WHERE id=6;"
sqlite3 -header -column "$DB" "SELECT id, phone, name, role, branch_id FROM users WHERE id=6;"
