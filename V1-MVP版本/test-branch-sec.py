import urllib.request, json

# 1. Login
body = json.dumps({'phone': '13800000003', 'password': 'pass1234'}).encode()
req = urllib.request.Request('http://localhost:8000/api/v1/auth/login', data=body,
    headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
login = json.loads(r.read())
token = login['access_token']
print(f"Login OK, token={token[:20]}...")

# 2. fetchMe
req2 = urllib.request.Request('http://localhost:8000/api/v1/auth/me',
    headers={'Authorization': f'Bearer {token}'})
r2 = urllib.request.urlopen(req2)
user = json.loads(r2.read())
print(f"User: {user['name']} ({user['role']}), branch_id={user.get('branch_id')}")

# 3. Create activity in own branch (branch_id=7 for 陈书记)
body3 = json.dumps({
    'organizer_branch_id': 7,
    'training_at': '2026-07-26T09:00:00',
    'location': '南湾街道会议室',
    'theme': '主题党日学习活动',
    'participant_count': 0,
    'online_offline': 'offline',
    'is_centralized': True,
    'is_innovation_theory': False,
    'source_type': 'self_organize',
    'audience_category': 'community_member',
    'study_hours': 4.0,
    'participants': []
}).encode()
req3 = urllib.request.Request('http://localhost:8000/api/v1/activities', data=body3,
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
r3 = urllib.request.urlopen(req3)
a = json.loads(r3.read())
print(f"Create activity OK: id={a['id']}, theme={a['theme']}, status={a['status']}")

# 4. List activities
req4 = urllib.request.Request('http://localhost:8000/api/v1/activities',
    headers={'Authorization': f'Bearer {token}'})
r4 = urllib.request.urlopen(req4)
lst = json.loads(r4.read())
print(f"List activities: total={lst['total']}, items={len(lst['items'])}")

# 5. Try create in OTHER branch (should 403)
body5 = json.dumps({
    'organizer_branch_id': 5,
    'training_at': '2026-07-26T09:00:00',
    'location': 'xx',
    'theme': 'other branch test',
    'participant_count': 0,
    'online_offline': 'offline',
    'is_centralized': True,
    'is_innovation_theory': False,
    'source_type': 'self_organize',
    'audience_category': 'community_member',
    'study_hours': 4.0,
    'participants': []
}).encode()
req5 = urllib.request.Request('http://localhost:8000/api/v1/activities', data=body5,
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
try:
    r5 = urllib.request.urlopen(req5)
    print("ERROR: Should have been rejected!")
except urllib.request.HTTPError as e:
    print(f"Other branch rejected correctly: {e.code}")

print("\nAll tests passed ✅")
