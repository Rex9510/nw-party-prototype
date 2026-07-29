"""Test API directly on the server - uses JWT secret directly."""
import json, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from jose import jwt

HOST = "http://127.0.0.1:8000"
SECRET = "bJU0IISYL2PsI3w6qhH9vvHqDTF-iSdvmPvFi1jYfs1YZIQffj2j90waORLMscPt"
ALGO = "HS256"

# Generate a token directly
payload = {
    "sub": "1",
    "role": "system_admin",
    "exp": datetime.now(timezone.utc) + timedelta(hours=2),
    "type": "access",
}
token = jwt.encode(payload, SECRET, algorithm=ALGO)
print(f"TOKEN gen OK: {token[:60]}...")

def test(body, label, expect_ok=True):
    req = urllib.request.Request(
        f"{HOST}/api/v1/activities",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    try:
        resp = urllib.request.urlopen(req)
        r = resp.read().decode()
        if expect_ok:
            print(f"✅ [{label}] OK: {r[:200]}")
        else:
            print(f"❌ [{label}] Expected error but got OK: {r[:200]}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        if expect_ok:
            print(f"❌ [{label}] Unexpected ERR {e.code}: {err[:400]}")
        else:
            print(f"✅ [{label}] Got expected ERR {e.code}: {err[:400]}")

# Test 1: 集中学习=是 but no study_methods field at all (NOT sent)
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "participants": [], "photo_count": 0
}, "无study_methods字段", expect_ok=False)

# Test 2: 集中学习=是 + study_methods=[] 
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "study_methods": [],
    "participants": [], "photo_count": 0
}, "study_methods=[]", expect_ok=False)

# Test 3: 集中学习=否, no study_methods 
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "participants": [], "photo_count": 0
}, "集中学习=否", expect_ok=True)

# Test 4: 上级送课 with upper_org=null (not in body)
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "upper_send",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "participants": [], "photo_count": 0
}, "上级送课+无upper_org", expect_ok=False)

# Test 5: 上级送课 with upper_org="" 
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "upper_send",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "upper_org": "",
    "participants": [], "photo_count": 0
}, "上级送课+upper_org=\"\"", expect_ok=False)

# Test 6: audience_category=[]
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": [],
    "study_hours": 2,
    "participants": [], "photo_count": 0
}, "空audience_category", expect_ok=False)

# Test 7: online_offline invalid
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "INVALID",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "participants": [], "photo_count": 0
}, "online_offline非法值", expect_ok=False)

# Test 8: study_hours=null with submit (should fail frontend? But what about backend validation?)
# Actually ActivityCreate inherits ActivityBase, study_hours is Optional

# Test 9: is_centralized sent as string "true" instead of bool
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": "true", "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "study_methods": ["party_meeting"],
    "participants": [], "photo_count": 0
}, "is_centralized=\"true\" 字符串", expect_ok=False)

# Test 10: is_centralized sent as string "false"
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": "false", "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "participants": [], "photo_count": 0
}, "is_centralized=\"false\" 字符串", expect_ok=False)
