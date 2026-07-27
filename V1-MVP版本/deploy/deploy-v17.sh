#!/bin/bash
set -e
cd /var/www/nwparty/frontend
# 清理前一次的 dist（之前是错误解压的 zip）
mv dist dist.zip-broken
mkdir dist
cd dist
tar -xzf /tmp/dist-2026-07-26-2101-v17.tar.gz --strip-components=1
echo OK
ls -la | head -8
echo "---"
ls assets/ | head -3
