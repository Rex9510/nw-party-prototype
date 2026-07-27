#!/usr/bin/env bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
curl -s "http://127.0.0.1:8000/api/v1/activities/13" \
  -H "Authorization: Bearer $TOKEN" > /tmp/act13.json
python3 << 'PY'
import json
d = json.load(open('/tmp/act13.json'))
print('=== top-level keys ===')
for k in sorted(d.keys()):
    print(f'  {k}: {d.get(k)!r}'[:200])
print()
print('=== participants ===')
for p in d.get('participants', []):
    print(f'  {p}')
print()
print('=== attachments ===')
for a in d.get('attachments', []):
    print(f'  id={a.get("id")} kind={a.get("kind")} file_url_len={len(a.get("file_url",""))}')
PY
