"""SSH 到远程服务器，检查 OpenAPI schema 中 audience_category 的类型。"""
import json, subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

remote_script = r"""set -e
curl -s http://127.0.0.1:8000/openapi.json > /tmp/openapi.json
python3 << 'PYEOF'
import json
d = json.load(open('/tmp/openapi.json'))
# 找 ActivityBase
for sname in ('ActivityBase', 'ActivityCreate', 'ActivityOut'):
    s = d.get('components',{}).get('schemas',{}).get(sname,{})
    if s and 'audience_category' in s.get('properties',{}):
        print(f'=== {sname} ===')
        ac = s['properties']['audience_category']
        print(json.dumps(ac, indent=2, ensure_ascii=False))
        print()
PYEOF
"""

cmd = ['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no', SSH_HOST, remote_script]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
print('STDOUT:', r.stdout)
if r.stderr:
    print('STDERR:', r.stderr[:500])
if r.returncode != 0:
    print(f'EXIT CODE: {r.returncode}')
    sys.exit(1)
