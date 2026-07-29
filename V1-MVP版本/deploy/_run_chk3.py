"""Check import - insert backend dir into sys.path"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

py_code = """
import sys, os
sys.path.insert(0, '/var/www/nwparty/src/backend')
os.chdir('/var/www/nwparty/src/backend')

print('CWD:', os.getcwd())
print('=== sys.path[:3] ===')
for p in sys.path[:3]:
    print(p)

print()
from app.schemas.activity import ActivityBase
f = ActivityBase.model_fields.get('audience_category')
print('IMPORT OK')
print('audience_category annotation:', f.annotation)
if f.default is not None:
    print('audience_category default:', f.default)

# also check for new fields
for field_name in ['upper_org', 'study_methods']:
    f2 = ActivityBase.model_fields.get(field_name)
    if f2:
        print(f'{field_name}: annotation={f2.annotation}')
    else:
        print(f'{field_name}: NOT FOUND')
"""

# write to /tmp on server
subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST,
    'cat > /tmp/_chk_import3.py << '"'"'EOF'"'"'\n' + py_code + '\nEOF'], timeout=15, capture_output=True)

r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST,
    'source /var/www/nwparty/venv/bin/activate && python3 /tmp/_chk_import3.py 2>&1'],
    capture_output=True, timeout=15, errors='replace')

print(r.stdout)
err = r.stderr.strip()
if err and 'IO is still pending' not in err and 'Connection' not in err:
    print('STDERR:', err[:500])
