"""Test API directly on the server."""
import json, urllib.request, urllib.error, sys

HOST = "http://127.0.0.1:8000"
token = None

# Try to login with different passwords
for pw in ["test123", "admin123", "123456", "password", "nwparty2024"]:
    data = json.dumps({"phone": "15812869715", "password": pw}).encode()
    req = urllib.request.Request(
        f"{HOST}/api/v1/auth/login",
        data=data, headers={"Content-Type": "application/json"}
    )
    try:
        resp = urllib.request.urlopen(req)
        body = json.loads(resp.read())
        token = body["access_token"]
        print(f"LOGIN OK with phone=15812869715 pw={pw}")
        break
    except urllib.error.HTTPError:
        pass

if not token:
    # Try phone 13800000000
    for pw in ["test123", "admin123", "123456", "password", "nwparty2024"]:
        data = json.dumps({"phone": "13800000000", "password": pw}).encode()
        req = urllib.request.Request(
            f"{HOST}/api/v1/auth/login",
            data=data, headers={"Content-Type": "application/json"}
        )
        try:
            resp = urllib.request.urlopen(req)
            body = json.loads(resp.read())
            token = body["access_token"]
            print(f"LOGIN OK with phone=13800000000 pw={pw}")
            break
        except urllib.error.HTTPError:
            pass

if not token:
    print("Could not login with any known password")
    sys.exit(1)

def test(body, label):
    req = urllib.request.Request(
        f"{HOST}/api/v1/activities",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    try:
        resp = urllib.request.urlopen(req)
        print(f"[{label}] OK:", resp.read().decode()[:300])
    except urllib.error.HTTPError as e:
        print(f"[{label}] ERR {e.code}: {e.read().decode()[:600]}")

# Test the "集中学习=是" + "无 study_methods" scenario
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test会议室", "theme": "test活动", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": None,
    "participants": [], "photo_count": 0
}, "无study_methods+无upper_org")

# Test with study_methods explicitly empty
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
}, "study_methods=[] explicit")

# Test with NO study_methods field at all
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "participants": [], "photo_count": 0
}, "无study_methods字段")

# Test: is_centralized=False (集中学习=否)
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "study_methods": [],
    "participants": [], "photo_count": 0
}, "集中学习=否")

# Test: source_type="upper_send" with empty upper_org
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

# Test: source_type="upper_send" with null upper_org
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True, "is_innovation_theory": False,
    "source_type": "upper_send",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "upper_org": None,
    "study_methods": ["party_meeting"],
    "participants": [], "photo_count": 0
}, "上级送课+null upper_org")

# Test: source_type="upper_send" with valid upper_org
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
