"""检查启动脚本"""
import subprocess

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

def run(cmd):
    r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
        '-o', 'LogLevel=QUIET', SSH_HOST, cmd],
        capture_output=True, timeout=30, errors='replace')
    out = r.stdout.strip()
    if out:
        print(out)

run('cat /var/www/nwparty/config/start-backend.sh')
print('===')
run('ls -la /var/www/nwparty/src/backend/app/schemas/')
print('===')
run('sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 show nwparty-api 2>&1')
