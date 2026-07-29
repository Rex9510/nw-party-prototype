"""Simplified remote checks - encoding safe"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

def run(cmd):
    try:
        r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
            '-o', 'LogLevel=QUIET', SSH_HOST, cmd],
            capture_output=True, timeout=30, errors='replace')
        out = r.stdout.strip()
        if out:
            # safe print
            sys.stdout.buffer.write(out.encode('utf-8', errors='replace') + b'\n')
        if r.returncode and '2>&1' not in cmd and r.returncode != 255:
            print(f'  exit={r.returncode}')
    except Exception as e:
        print(f'ERROR: {e}')

run('ls -la /var/www/nwparty/src/backend/app/schemas/__pycache__/')
run('source /var/www/nwparty/venv/bin/activate && cd /var/www/nwparty/src/backend && python3 -c "from app.schemas.activity import ActivityBase; f=ActivityBase.model_fields[\"audience_category\"]; print(f\"annotation: {f.annotation}, default: {f.default}\")"')
run('ll /proc/$(cat /var/www/nwparty/src/backend/gunicorn.pid 2>/dev/null)/fd/ 2>/dev/null | head -5 || echo no_pid_file')
run('ss -tlnp | grep 8000')
run('find /var/www/nwparty/venv -name "*.egg-link" -o -name "*.pth" 2>/dev/null')
run('cat /var/www/nwparty/ecosystem.config.cjs')
