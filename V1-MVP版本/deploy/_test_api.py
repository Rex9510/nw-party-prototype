"""Test create activity via remote API with proper token"""
import subprocess, json, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

# Write and run test script on the server
test_script = r"""
set -e
source /var/www/nwparty/venv/bin/activate
cd /var/www/nwparty/src/backend

# Generate token
export $(cat /var/www/nwparty/.env | grep -v "^#" | xargs)
TOKEN=$(python3 -c "
import sys
sys.path.insert(0, '.')
from app.core.security import create_access_token
print(create_access_token(data={'sub': '1'}))
" 2>&1 | tail -1)
echo "TOKEN=$TOKEN"

# Test POST
RESULT=$(curl -s -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"organizer_branch_id":1,"training_at":"2026-07-28T10:00:00","location":"\u6d4b\u8bd5\u5730\u70b9","theme":"\u6d4b\u8bd5\u6d3b\u52a8","participant_count":10,"online_offline":"offline","is_centralized":false,"is_innovation_theory":false,"source_type":"self_organize","audience_category":["party_member"],"study_hours":1,"photo_count":1}' 2>&1)
echo "RESULT=$RESULT"
"""

r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST, test_script],
    capture_output=True, timeout=30, errors='replace')

print('STDOUT:')
print(r.stdout[:3000])
if r.stderr.strip() and 'IO is still pending' not in r.stderr:
    print('STDERR:', r.stderr[:500])
print(f'EXIT: {r.returncode}')
