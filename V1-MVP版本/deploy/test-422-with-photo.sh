#!/usr/bin/env bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000003","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# 模拟前端真实 payload（含已上传图片 dataURL）
echo "--- 1) 带 1 张空 dataURL 图片 ---"
DATAURL="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAA"
curl -s -w '\nHTTP=%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"organizer_branch_id\": 5,
    \"training_at\": \"2026-07-26T14:00:00\",
    \"location\": \"测试会议室\",
    \"theme\": \"保存草稿\",
    \"participant_count\": 1,
    \"online_offline\": \"offline\",
    \"is_centralized\": true,
    \"is_innovation_theory\": true,
    \"source_type\": \"self_organize\",
    \"audience_category\": \"party_member\",
    \"study_hours\": null,
    \"photo_count\": 1,
    \"participants\": [{\"member_id\": 4, \"study_hours\": 0}]
  }"
