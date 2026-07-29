"""Check startup - encoding safe"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

def run(cmd):
    r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
        '-o', 'LogLevel=QUIET', SSH_HOST, cmd],
        capture_output=True, timeout=30, errors='replace')
    out = r.stdout.strip()
    if out:
        sys.stdout.buffer.write(out.encode('utf-8', errors='replace') + b'\n')
    err = r.stderr.strip()
    if err and 'IO is still pending' not in err:
        sys.stdout.buffer.write(b'ERR: ')
        sys.stdout.buffer.write(err.encode('utf-8', errors='replace')[:500] + b'\n')

run('cat /var/www/nwparty/config/start-backend.sh')
print('===')
run('ls -la /var/www/nwparty/src/backend/app/schemas/')
print('===')
run('sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 show nwparty-api 2>&1')
print('===')
run('stat /var/www/nwparty/src/backend/app/schemas/__pycache__/activity.cpython-312.pyc')
