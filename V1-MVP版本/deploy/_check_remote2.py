"""逐个执行远程命令避免编码问题"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

def run(cmd, desc=''):
    print(f'=== {desc} ===')
    r = subprocess.run(
        ['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
         '-o', 'LogLevel=QUIET', SSH_HOST, cmd],
        capture_output=True, timeout=30, errors='replace'
    )
    if r.stdout.strip():
        print(r.stdout)
    if r.stderr.strip():
        s = r.stderr.strip()
        # skip "close - IO is still pending" noise
        if 'IO is still pending' not in s:
            print('ERR:', s[:500])
    if r.returncode != 0 and r.returncode != 255:
        print(f'WARN: exit code {r.returncode}')

run('ls -la /var/www/nwparty/src/backend/app/schemas/activity.py', 'remote activity.py')
run('ls -la /var/www/nwparty/src/backend/app/schemas/__pycache__/activity*.pyc 2>/dev/null || echo no_pyc', 'pyc files')
run('find /var/www/nwparty/src/backend -name __pycache__ -type d 2>/dev/null', 'pycache dirs')
run('cat /var/www/nwparty/src/backend/app/__init__.py 2>/dev/null; echo "---"; cat /var/www/nwparty/src/backend/app/schemas/__init__.py 2>/dev/null; echo "---end---"', 'init files')
run('find /var/www/nwparty/venv -name "*.egg-link" -type f 2>/dev/null || echo no_egg_link', 'egg-link')
run('sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 list 2>&1', 'pm2 list')
run('ps aux | grep -E "gunicorn|uvicorn" | grep -v grep || echo no_gunicorn', 'processes')
