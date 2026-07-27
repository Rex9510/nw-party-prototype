#!/usr/bin/env bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000003","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# 模拟：未选"现场照片"但选了"附件"；并且没填学时
echo "--- 1) 复现：未传 photo_count（前端写真是 photo_count: photoList.length）---"
curl -s -w '\nHTTP=%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_branch_id": 5,
    "training_at": "2026-07-26T14:00:00",
    "location": "测试会议室",
    "theme": "草稿无学时",
    "participant_count": 1,
    "online_offline": "offline",
    "is_centralized": true,
    "is_innovation_theory": true,
    "source_type": "self_organize",
    "audience_category": "party_member",
    "study_hours": null,
    "participants": [{"member_id": 4, "study_hours": 0}]
  }'

echo
echo "--- 2) 复现：没 photo_count 字段（前端实际 payload 没这个？）---"
# 看前端 onSave 里 body 有 photo_count
# 但前端的 photoList 可能是空数组（如果陈书记没传照片）
# 所以 photo_count = 0
# 让我看后端：photo_count = body.photo_count
# 然后 dump() exclude 这个字段
# 但 Pydantic 在创建时是 required（默认 0）
# 那 422 应该是其他原因

# 测个更全的 payload:
echo "--- 3) 带 photo_count 字段 ---"
curl -s -w '\nHTTP=%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_branch_id": 5,
    "training_at": "2026-07-26T14:00:00",
    "location": "测试会议室",
    "theme": "草稿带 photo_count",
    "participant_count": 1,
    "online_offline": "offline",
    "is_centralized": true,
    "is_innovation_theory": true,
    "source_type": "self_organize",
    "audience_category": "party_member",
    "study_hours": null,
    "photo_count": 0,
    "participants": [{"member_id": 4, "study_hours": 0}]
  }'
