#!/usr/bin/env python3
"""Generate JWT token for testing"""
import sys, json, os
sys.path.insert(0, '/var/www/nwparty/src/backend')
os.environ['JWT_SECRET'] = 'bJU0IISYL2PsI3w6qhH9vvHqDTF-iSdvmPvFi1jYfs1YZIQffj2j90waORLMscPt'
os.environ['JWT_ALGORITHM'] = 'HS256'
os.environ['ACCESS_TOKEN_EXPIRE_MINUTES'] = '10080'

from app.core.security import create_access_token
token = create_access_token(data={"sub": "1"})
print(token)

# Also test creating an activity
import urllib.request, urllib.error

payload = json.dumps({
    "organizer_branch_id": 1,
    "training_at": "2026-07-28T10:00:00",
    "location": "test",
    "theme": "test",
    "participant_count": 10,
    "online_offline": "offline",
    "is_centralized": False,
    "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 1,
    "photo_count": 1
}).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/activities',
    data=payload,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    method='POST'
)

try:
    resp = urllib.request.urlopen(req, timeout=10)
    print('CREATE OK')
    print(resp.status)
    print(resp.read().decode('utf-8')[:500])
except urllib.error.HTTPError as e:
    print(f'HTTP ERROR {e.code}')
    print(e.read().decode('utf-8')[:1000])
except Exception as e:
    print(f'ERROR: {e}')
