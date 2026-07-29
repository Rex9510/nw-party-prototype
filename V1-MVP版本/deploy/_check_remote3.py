"""Simplified remote checks"""
import subprocess

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

def run(cmd):
    r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
        '-o', 'LogLevel=QUIET', SSH_HOST, cmd], capture_output=True, timeout=30, errors='replace')
    out = r.stdout.strip()
    if out:
        print(out)
    if r.returncode and 'no_' not in cmd:
        print(f'  exit={r.returncode}')

run('ls -la /var/www/nwparty/src/backend/app/schemas/activity.py && wc -l /var/www/nwparty/src/backend/app/schemas/activity.py')
run('ls /var/www/nwparty/src/backend/app/schemas/__pycache__/activity*.pyc 2>/dev/null || echo no_pyc')
run('cat /var/www/nwparty/src/backend/app/__init__.py 2>/dev/null; echo "---SEP---"; cat /var/www/nwparty/src/backend/app/schemas/__init__.py 2>/dev/null; echo "---SEP---"; cat /var/www/nwparty/src/backend/app/api/__init__.py 2>/dev/null')
run('sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 list 2>&1')
run('source /var/www/nwparty/venv/bin/activate && cd /var/www/nwparty/src/backend && python3 -c "from app.schemas.activity import ActivityBase; f=ActivityBase.model_fields[\"audience_category\"]; print(f\"annotation: {f.annotation}, default: {f.default}\")"')
