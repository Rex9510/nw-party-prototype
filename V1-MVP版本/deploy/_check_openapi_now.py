"""Check current OpenAPI schema for audience_category"""
import subprocess, json, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST,
    'curl -s http://127.0.0.1:8000/openapi.json | python3 -c "import json,sys;d=json.load(sys.stdin);act=d[\"components\"][\"schemas\"].get(\"ActivityCreate\",{});ac=act.get(\"properties\",{}).get(\"audience_category\",{});print(json.dumps(ac,indent=2))"'],
    capture_output=True, timeout=15, errors='replace')

out = r.stdout.strip()
print('ActivityCreate.audience_category:')
print(out)

# also check ActivityOut
r2 = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST,
    'curl -s http://127.0.0.1:8000/openapi.json | python3 -c "import json,sys;d=json.load(sys.stdin);act=d[\"components\"][\"schemas\"].get(\"ActivityOut\",{});ac=act.get(\"properties\",{}).get(\"audience_category\",{});print(json.dumps(ac,indent=2))"'],
    capture_output=True, timeout=15, errors='replace')
print('ActivityOut.audience_category:')
print(r2.stdout.strip())
