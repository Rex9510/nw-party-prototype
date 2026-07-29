"""Debug the audience_category issue."""
import json, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from jose import jwt

HOST = "http://127.0.0.1:8000"
SECRET = "bJU0IISYL2PsI3w6qhH9vvHqDTF-iSdvmPvFi1jYfs1YZIQffj2j90waORLMscPt"
ALGO = "HS256"

payload = {
    "sub": "1",
    "role": "system_admin",
    "exp": datetime.now(timezone.utc) + timedelta(hours=2),
    "type": "access",
}
token = jwt.encode(payload, SECRET, algorithm=ALGO)

def test(body, label):
    req = urllib.request.Request(
        f"{HOST}/api/v1/activities",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    try:
        resp = urllib.request.urlopen(req)
        print(f"[{label}] ✅ OK: {resp.read().decode()[:300]}")
    except urllib.error.HTTPError as e:
        print(f"[{label}] {e.code}: {e.read().decode()[:500]}")

# Test: audience_category 传字符串（老格式）
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": "party_member",
    "study_hours": 2,
    "participants": [], "photo_count": 0
}, "audience_category 传字符串")

# Test: audience_category 传数组
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "participants": [], "photo_count": 0
}, "audience_category 传数组")

# Test: audience_category 传双元素数组
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member", "community_member"],
    "study_hours": 2,
    "participants": [], "photo_count": 0
}, "audience_category 双元素数组")
