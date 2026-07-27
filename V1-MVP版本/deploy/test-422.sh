#!/usr/bin/env bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000003","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "--- 用陈书记账号提交一个没学时的活动，模拟保存草稿 ---"
curl -s -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_branch_id": 5,
    "training_at": "2026-07-26T14:00:00",
    "location": "测试会议室",
    "theme": "测试保存草稿报错",
    "participant_count": 1,
    "online_offline": "offline",
    "is_centralized": true,
    "is_innovation_theory": true,
    "source_type": "self_organize",
    "audience_category": "party_member",
    "study_hours": null,
    "lecturer_name": null,
    "lecturer_bio": null,
    "participants": [{"member_id": 4, "study_hours": 0}]
  }' | python3 -m json.tool
