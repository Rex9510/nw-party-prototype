#!/usr/bin/env bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000003","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "--- 草稿：study_hours + participants[].study_hours 都是 null ---"
curl -s -w '\nHTTP=%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_branch_id": 5,
    "training_at": "2026-07-26T14:00:00",
    "location": "测试",
    "theme": "草稿 null hours",
    "participant_count": 2,
    "online_offline": "offline",
    "is_centralized": true,
    "is_innovation_theory": true,
    "source_type": "self_organize",
    "audience_category": "party_member",
    "study_hours": null,
    "photo_count": 1,
    "participants": [
      {"member_id": 4, "study_hours": null, "attendance_status": "signed"},
      {"member_id": 5, "study_hours": null, "attendance_status": "signed"}
    ]
  }' | python3 -m json.tool 2>&1 | head -30
