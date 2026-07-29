"""Test creating an activity with a valid token."""
import json, urllib.request, urllib.error, sys

HOST = "http://127.0.0.1:8000"

# Step 1: Login
print("=== LOGIN ===")
data = json.dumps({"phone": "13800000000", "password": "admin123"}).encode()
req = urllib.request.Request(
    f"{HOST}/api/v1/auth/login",
    data=data, headers={"Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req)
    body = json.loads(resp.read())
    token = body["access_token"]
    print("TOKEN ok:", token[:60])
except urllib.error.HTTPError as e:
    print("LOGIN FAILED:", e.code, e.read().decode()[:500])
    sys.exit(1)

# Test scenarios
def test(body, label):
    req = urllib.request.Request(
        f"{HOST}/api/v1/activities",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    try:
        resp = urllib.request.urlopen(req)
        print(f"[{label}] OK:", resp.read().decode()[:200])
    except urllib.error.HTTPError as e:
        print(f"[{label}] ERR {e.code}: {e.read().decode()[:600]}")

# Test A: "自组织" + "集中学习=是" + "是否有创新" - with study_hours=null
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": None,
    "upper_org": None,
    "study_methods": [],
    "participants": [], "photo_count": 0
}, "集中学习=是+空study_methods")

# Test B: 集中学习=false
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": None,
    "participants": [], "photo_count": 0
}, "集中学习=false")

# Test C: 上级送课 without 具体部门
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True, "is_innovation_theory": False,
    "source_type": "upper_send",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "upper_org": "",
    "study_methods": ["party_meeting"],
    "participants": [], "photo_count": 0
}, "上级送课+空upper_org")

# Test D: 上级送课 + proper upper_org
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True, "is_innovation_theory": False,
    "source_type": "upper_send",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "upper_org": "区委组织部",
    "study_methods": ["party_meeting"],
    "participants": [], "photo_count": 0
}, "上级送课+完整")

# Test E: What about empty audience_category?
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": [],
    "study_hours": None,
    "participants": [], "photo_count": 0
}, "空audience_category")
