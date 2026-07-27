#!/usr/bin/env bash
echo "=== A) system_admin (13800000000) - 应看到全街道 ==="
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
curl -s "http://127.0.0.1:8000/api/v1/stats/stats?period=year&year=2026" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('label:', d.get('label'))
for it in d.get('items', []):
    print(f\"  {it['label']}: {it['session_count']} 场, {it['participant_count']} 人\")
"

echo
echo "=== B) 街道负责人 (13800000001) - 应看到全街道 ==="
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000001","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
curl -s "http://127.0.0.1:8000/api/v1/stats/stats?period=year&year=2026" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('label:', d.get('label'))
for it in d.get('items', []):
    print(f\"  {it['label']}: {it['session_count']} 场, {it['participant_count']} 人\")
"

echo
echo "=== C) 社区组织委员 (13800000002) - 应只看自己社区 (现在挪到 厦村社区 id=3) ==="
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000002","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
curl -s "http://127.0.0.1:8000/api/v1/stats/stats?period=year&year=2026" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('label:', d.get('label'))
for it in d.get('items', []):
    print(f\"  {it['label']}: {it['session_count']} 场, {it['participant_count']} 人\")
"

echo
echo "=== D) 当前 activities 数据 ==="
sqlite3 -header -column /var/www/nwparty/data/nwparty.db "SELECT id, theme, organizer_branch_id, community_id, status, source_type, audience_category FROM activities;"
