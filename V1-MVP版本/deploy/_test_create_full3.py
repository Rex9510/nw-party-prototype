#!/usr/bin/env python3
"""Test create activity with valid branch_id=5"""
import sys, json, os, urllib.request, urllib.error
sys.path.insert(0, '/var/www/nwparty/src/backend')
os.environ['JWT_SECRET'] = 'bJU0IISYL2PsI3w6qhH9vvHqDTF-iSdvmPvFi1jYfs1YZIQffj2j90waORLMscPt'
os.environ['JWT_ALGORITHM'] = 'HS256'
os.environ['ACCESS_TOKEN_EXPIRE_MINUTES'] = '10080'

from app.core.security import create_access_token
token = create_access_token(subject="1")
print(f'Token OK ({len(token)} chars)')

# Test 1: basic create (self_organize, not centralized)
payload = json.dumps({
    "organizer_branch_id": 5,
    "training_at": "2026-07-28T10:00:00",
    "location": "test location",
    "theme": "test activity",
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
    print(f'\nTest 1 (basic): CREATE OK status={resp.status}')
    body = resp.read().decode('utf-8')
    print(body[:500])
except urllib.error.HTTPError as e:
    print(f'\nTest 1: HTTP ERROR {e.code}')
    print(e.read().decode('utf-8')[:1000])
except Exception as e:
    print(f'\nTest 1 ERROR: {e}')

# Test 2: centralized with study_methods
payload2 = json.dumps({
    "organizer_branch_id": 5,
    "training_at": "2026-07-29T10:00:00",
    "location": "test centralized",
    "theme": "test centralized activity",
    "participant_count": 20,
    "online_offline": "online",
    "is_centralized": True,
    "is_innovation_theory": True,
    "source_type": "upper_send",
    "upper_org": "区委组织部",
    "audience_category": ["party_member", "community_member"],
    "study_hours": 2,
    "study_methods": ["party_meeting", "theme_day"],
    "photo_count": 3
}).encode('utf-8')

req2 = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/activities',
    data=payload2,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    method='POST'
)

try:
    resp2 = urllib.request.urlopen(req2, timeout=10)
    print(f'\nTest 2 (centralized+upper): CREATE OK status={resp2.status}')
    body2 = resp2.read().decode('utf-8')
    print(body2[:500])
except urllib.error.HTTPError as e:
    print(f'\nTest 2: HTTP ERROR {e.code}')
    print(e.read().decode('utf-8')[:1000])
except Exception as e:
    print(f'\nTest 2 ERROR: {e}')
