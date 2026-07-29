"""Check import path on remote server"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'
LOCAL_PY = r'E:\new party\nw-party-prototype\V1-MVP版本\deploy\_chk_import.py'
REMOTE_PY = '/tmp/_chk_import.py'

# scp
subprocess.run(['scp', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    LOCAL_PY, f'{SSH_HOST}:{REMOTE_PY}'], timeout=15)

# run
r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST,
    'source /var/www/nwparty/venv/bin/activate && cd /var/www/nwparty/src/backend && python3 /tmp/_chk_import.py 2>&1'],
    capture_output=True, timeout=15, errors='replace')

print(r.stdout)
err = r.stderr.strip()
if err and 'IO is still pending' not in err:
    print('STDERR:', err[:500])
