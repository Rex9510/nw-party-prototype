"""Test create activity via remote API with proper token"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

test_script = 'set -e\n'
test_script += 'source /var/www/nwparty/venv/bin/activate\n'
test_script += 'cd /var/www/nwparty/src/backend\n'
test_script += 'TOKEN=$(python3 -c "import sys; sys.path.insert(0,\".\"); from app.core.security import create_access_token; print(create_access_token(data={\'sub\': \'1\'}))" 2>&1 | tail -1)\n'
test_script += 'echo "TOKEN=$TOKEN"\n'
test_script += 'curl -s -X POST http://127.0.0.1:8000/api/v1/activities \\\n'
test_script += '  -H "Authorization: Bearer $TOKEN" \\\n'
test_script += '  -H "Content-Type: application/json" \\\n'
test_script += "  -d '{\"organizer_branch_id\":1,\"training_at\":\"2026-07-28T10:00:00\",\"location\":\"test\",\"theme\":\"test\",\"participant_count\":10,\"online_offline\":\"offline\",\"is_centralized\":false,\"is_innovation_theory\":false,\"source_type\":\"self_organize\",\"audience_category\":[\"party_member\"],\"study_hours\":1,\"photo_count\":1}'\n"

r = subprocess.run(['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
    '-o', 'LogLevel=QUIET', SSH_HOST, test_script],
    capture_output=True, timeout=30, errors='replace')

sys.stdout.buffer.write(r.stdout.encode('utf-8', errors='replace')[:3000])
if r.stderr.strip() and 'IO is still pending' not in r.stderr:
    print('\nSTDERR:', r.stderr[:500])
print(f'\nEXIT: {r.returncode}')
