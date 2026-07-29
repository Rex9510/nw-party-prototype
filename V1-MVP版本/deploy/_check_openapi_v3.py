"""Check OpenAPI schema on remote - write script to /tmp first"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

# Step 1: write checker script to /tmp on server
script = """#!/usr/bin/env python3
import json, sys
d = json.load(sys.stdin)
sch = d.get('components',{}).get('schemas',{})
for k in sorted(sch.keys()):
    if 'Activity' in k:
        props = sch[k].get('properties',{})
        print(f'=== {k} ===')
        for pk, pv in props.items():
            t = pv.get('type','?')
            print(f'  {pk}: type={json.dumps(t) if isinstance(t,str) else t}, title={pv.get("title","")}')
        print()
"""

# Write remote script
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
    f.write(script)
    local_script = f.name

# scp it
subprocess.run(['scp', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    local_script, f'{SSH_HOST}:/tmp/_check_schema.py'], timeout=15)

# run remote: curl openapi -> python script
r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST,
    'curl -s http://127.0.0.1:8000/openapi.json | python3 /tmp/_check_schema.py 2>&1'],
    capture_output=True, timeout=15, errors='replace')

print(r.stdout)
if r.stderr.strip() and 'IO is still pending' not in r.stderr:
    print('ERR:', r.stderr[:500])

# cleanup
import os; os.unlink(local_script)
