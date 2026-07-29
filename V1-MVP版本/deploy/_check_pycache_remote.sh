#!/bin/bash
set -e
echo "=== __pycache__ files ==="
find /var/www/nwparty/src/backend -name '*.pyc' -type f 2>/dev/null || echo "(none)"
echo ""
echo "=== schema pyc vs py ==="
ls -la /var/www/nwparty/src/backend/app/schemas/activity.py
ls -la /var/www/nwparty/src/backend/app/schemas/__pycache__/activity*.pyc 2>/dev/null || echo "(no pyc)"
echo ""
echo "=== pm2 list ==="
sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 list 2>/dev/null || echo "pm2 error"
echo ""
echo "=== gunicorn processes ==="
ps aux | grep -E 'gunicorn|uvicorn' | grep -v grep || echo "(no gunicorn/uvicorn)"
echo ""
echo "=== fresh import check ==="
source /var/www/nwparty/venv/bin/activate
cd /var/www/nwparty/src/backend
python3 -c "
import sys
for mod in list(sys.modules.keys()):
    if 'schemas' in mod or 'activity' in mod:
        del sys.modules[mod]
from app.schemas.activity import ActivityBase
f = ActivityBase.model_fields['audience_category']
print('audience_category annotation:', f.annotation)
print('audience_category default:', f.default)
" 2>&1
echo ""
echo "=== check backend app __init__.py ==="
cat /var/www/nwparty/src/backend/app/__init__.py 2>/dev/null || echo "(no __init__.py)"
cat /var/www/nwparty/src/backend/app/schemas/__init__.py 2>/dev/null || echo "(no schemas __init__.py)"
echo ""
echo "=== check for egg-info ==="
find /var/www/nwparty/venv -name '*.egg-link' -type f 2>/dev/null || echo "(no egg-link)"
