"""Test creating an activity via nginx proxy - WITHOUT auth (expect 401 or 422)."""
import json, urllib.request, urllib.error

def test(body, label):
    req = urllib.request.Request(
        "http://47.107.77.15:8081/api/v1/activities",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        resp = urllib.request.urlopen(req)
        print(f"[{label}] 200 OK:", resp.read().decode()[:300])
    except urllib.error.HTTPError as e:
        print(f"[{label}] {e.code}: {e.read().decode()[:500]}")

# Test 1: basic, no study_methods (集中学习=true)
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"], "study_hours": 2,
    "participants": [], "photo_count": 0
}, "集中学习=true, 无study_methods")

# Test 2: with study_methods
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True, "is_innovation_theory": False,
    "source_type": "upper_send",
    "audience_category": ["party_member"], "study_hours": 2,
    "upper_org": "区委组织部",
    "study_methods": ["party_meeting"],
    "participants": [], "photo_count": 0
}, "集中学习=true+study_methods, 上级送课+具体部门")

# Test 3: 集中学习=false, no study_methods
test({
    "organizer_branch_id": 1, "training_at": "2026-08-01T09:00:00",
    "location": "test", "theme": "test", "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": False, "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"], "study_hours": 2,
    "participants": [], "photo_count": 0
}, "集中学习=false, 无需study_methods")
