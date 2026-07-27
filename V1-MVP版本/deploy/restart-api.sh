#!/usr/bin/env bash
echo "--- 清 __pycache__ ---"
find /var/www/nwparty/src/backend -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null
find /var/www/nwparty/src/backend -name '*.pyc' -delete 2>/dev/null
echo "done"
echo "--- pm2 kill + start ---"
pm2 kill 2>&1 | tail -1
sleep 2
cd /var/www/nwparty
pm2 start ecosystem.config.cjs 2>&1 | tail -1
sleep 4
pm2 list
