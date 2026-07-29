"""检查远程服务器的 __pycache__ 目录和模块缓存状态"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

remote_script = r"""set -e
echo '=== __pycache__ files ==='
find /var/www/nwparty/src/backend -name '*.pyc' -type f 2>/dev/null
echo ''
echo '=== schema .pyc timestamps vs .py ==='
ls -la /var/www/nwparty/src/backend/app/schemas/activity.py
ls -la /var/www/nwparty/src/backend/app/schemas/__pycache__/activity*.pyc 2>/dev/null || echo '(no pyc)'
echo ''
echo '=== DB path check ==='
ls -la /var/www/nwparty/data/nwparty.db
echo ''
echo '=== pm2 list ==='
sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 list
echo ''
echo '=== uvicorn processes ==='
ps aux | grep -E 'gunicorn|uvicorn' | grep -v grep || echo '(no matching process)'
echo ''
echo '=== try uv run fresh ==='
source /var/www/nwparty/venv/bin/activate
cd /var/www/nwparty/src/backend
python3 -c "
import importlib
import sys
# 清除缓存
for mod in list(sys.modules.keys()):
    if 'schemas' in mod or 'activity' in mod:
        del sys.modules[mod]
from app.schemas.activity import ActivityBase
print('ActivityBase.audience_category:', ActivityBase.model_fields['audience_category'])
"
"""

cmd = ['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no', SSH_HOST, remote_script]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
print('STDOUT:')
print(r.stdout)
print('---STDERR---')
print(r.stderr[:1000] if r.stderr else '(none)')
print(f'EXIT: {r.returncode}')
