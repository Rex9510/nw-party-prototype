"""Debug OpenAPI schema - dump all property keys for ActivityBase"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST,
    'curl -s http://127.0.0.1:8000/openapi.json 2>/dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);sch=d.get(\"components\",{}).get(\"schemas\",{});print(\"ALL SCHEMAS:\",list(sch.keys()));[print(f\"\\n--- {k} ---\",json.dumps({kk:vv.get(\"type\",\"?\") for kk,vv in v.get(\"properties\",{}).items()},indent=2)) for k,v in sch.items() if \"Activity\" in k]" 2>&1'],
    capture_output=True, timeout=15, errors='replace')

print(r.stdout[:3000])
if r.stderr.strip() and 'IO is still pending' not in r.stderr:
    print('ERR:', r.stderr[:500])
