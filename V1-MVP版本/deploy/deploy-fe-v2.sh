#!/usr/bin/env bash
set -e
cd /var/www/nwparty/frontend
# 用 mv 代替 rm -rf（保留旧 dist 为带时间戳的备份）
TS=$(date +%H%M%S)
if [ -d "dist" ]; then
  mv dist "dist.bak.${TS}"
fi
mkdir -p dist
tar -xzf /tmp/nwparty-update-2026-07-26/dist.tar.gz -C dist
echo "--- DEPLOYED ---"
ls dist/assets/ | wc -l
echo "--- backup ---"
ls -d dist.bak.* 2>/dev/null || true
