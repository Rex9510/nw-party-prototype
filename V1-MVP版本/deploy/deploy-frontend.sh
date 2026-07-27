#!/usr/bin/env bash
# 部署 frontend dist
set -e
cd /var/www/nwparty/frontend
# 备份
if [ -d "dist" ]; then
  cp -r dist dist.bak.$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
fi
rm -rf dist
mkdir -p dist
tar -xzf /tmp/nwparty-update-2026-07-26/dist.tar.gz -C dist
echo "--- DEPLOYED ---"
ls -la dist/ | head -10
echo "---"
ls dist/assets/ | head -5
