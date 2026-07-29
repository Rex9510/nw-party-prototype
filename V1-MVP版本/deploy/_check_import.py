"""Check where Python imports the module from"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

py_code = r"""import sys, importlib
# show sys.path
print('=== sys.path ===')
for p in sys.path:
    print(p)

# find the module
try:
    spec = importlib.util.find_spec('app.schemas.activity')
    print('=== spec ===')
    print('origin:', spec.origin)
    print('name:', spec.name)
    print('loader:', spec.loader)
    if spec.submodule_search_locations:
        print('submodule_search_locations:', spec.submodule_search_locations)
except Exception as e:
    print('ERROR:', e)

# check if there are other app packages in sys.modules
print('=== other "app" in sys.modules ===')
for k, v in list(sys.modules.items()):
    if 'app' in k and 'activity' in k:
        print(k, getattr(v, '__file__', '?'))
"""

# Write to tmp file on server
import tempfile, os
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
    f.write(py_code)
    local_tmp = f.name

subprocess.run(['scp', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    local_tmp, f'{SSH_HOST}:/tmp/_check_import.py'], timeout=15)
os.unlink(local_tmp)

r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST,
    'source /var/www/nwparty/venv/bin/activate && cd /var/www/nwparty/src/backend && python3 /tmp/_check_import.py 2>&1'],
    capture_output=True, timeout=15, errors='replace')

print(r.stdout)
err = r.stderr.strip()
if err and 'IO is still pending' not in err:
    print('STDERR:', err[:500])
