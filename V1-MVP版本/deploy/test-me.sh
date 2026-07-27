#!/usr/bin/env bash
echo "=== /me for system_admin ==="
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
curl -s "http://127.0.0.1:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo
echo "=== /me for community_organizer (李委员, 厦村社区) ==="
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000002","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
curl -s "http://127.0.0.1:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo
echo "=== /stats for community_organizer (只看到 厦村社区 的 1 场) ==="
curl -s "http://127.0.0.1:8000/api/v1/stats/stats?period=year&year=2026" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('label:', d.get('label'))
for it in d.get('items', []):
    print(f\"  {it['label']}: {it['session_count']} 场, {it['participant_count']} 人\")
"
