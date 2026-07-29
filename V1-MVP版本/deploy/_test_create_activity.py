"""Test create activity via API with token"""
import subprocess, json, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

# Step 1: generate token
r1 = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST,
    'source /var/www/nwparty/venv/bin/activate && python3 -c "from app.core.security import create_access_token; print(create_access_token(data={\"sub\":\"1\"}))" 2>&1'],
    capture_output=True, timeout=15, errors='replace')

token = r1.stdout.strip().split('\n')[-1].strip()
if not token or len(token) < 20:
    print(f'Failed to get token: {r1.stdout[:200]}')
    sys.exit(1)
print(f'Token: {token[:60]}...')

# Step 2: try to create an activity
import urllib.request, urllib.error

# The start-backend.sh has exec so the process runs as the SSH user (root)
# Let me try using curl via SSH
payload = json.dumps({
    "organizer_branch_id": 1,
    "training_at": "2026-07-28T10:00:00",
    "location": "测试地点",
    "theme": "测试活动",
    "participant_count": 10,
    "online_offline": "offline",
    "is_centralized": False,
    "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 1,
    "photo_count": 1
})

curl_cmd = f"""curl -s -X POST http://127.0.0.1:8000/api/v1/activities \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{payload}' 2>&1"""

r2 = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST, curl_cmd],
    capture_output=True, timeout=15, errors='replace')

print('\nAPI Response:')
print(r2.stdout[:2000])
if r2.stderr.strip() and 'IO is still pending' not in r2.stderr:
    print('STDERR:', r2.stderr[:500])
