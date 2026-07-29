"""Test creating an activity via the API."""
import json
import urllib.request
import urllib.error
import sys

data = json.dumps({
    "organizer_branch_id": 1,
    "training_at": "2026-08-01T09:00:00",
    "location": "测试会议室",
    "theme": "测试活动",
    "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": True,
    "is_innovation_theory": False,
    "source_type": "self_organize",
    "audience_category": ["party_member"],
    "study_hours": 2,
    "participants": [],
    "photo_count": 0
}).encode()

req = urllib.request.Request(
    "http://47.107.77.15:8081/api/v1/activities",
    data=data,
    headers={"Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req)
    print("200 OK:", resp.read().decode()[:500])
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"ERROR {e.code}: {body[:1000]}")
