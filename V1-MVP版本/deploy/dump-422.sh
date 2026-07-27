#!/usr/bin/env bash
# 重现 422：模仿陈书记保存草稿的真实场景
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000003","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# 设想 payload：min content + 没有 photo_count 字段
# 前端 onSave 的 body 一定含 photo_count
# 但如果用户先选了 1 张照片再保存草稿，photo_count=1
# 试着：去掉 lecturer_name 字段
echo "--- A) 缺 lecturer_name ---"
curl -s -w '\nHTTP=%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_branch_id": 5,
    "training_at": "2026-07-26T14:00:00",
    "location": "测试",
    "theme": "主题",
    "participant_count": 1,
    "online_offline": "offline",
    "is_centralized": true,
    "is_innovation_theory": true,
    "source_type": "self_organize",
    "audience_category": "party_member",
    "study_hours": null,
    "photo_count": 1,
    "participants": []
  }'

echo
echo "--- B) audience_category 不在字典里 ---"
curl -s -w '\nHTTP=%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_branch_id": 5,
    "training_at": "2026-07-26T14:00:00",
    "location": "测试",
    "theme": "主题",
    "participant_count": 1,
    "online_offline": "offline",
    "is_centralized": true,
    "is_innovation_theory": true,
    "source_type": "self_organize",
    "audience_category": "INVALID",
    "study_hours": null,
    "photo_count": 1,
    "participants": []
  }'

echo
echo "--- C) source_type 不合法 ---"
curl -s -w '\nHTTP=%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_branch_id": 5,
    "training_at": "2026-07-26T14:00:00",
    "location": "测试",
    "theme": "主题",
    "participant_count": 1,
    "online_offline": "offline",
    "is_centralized": true,
    "is_innovation_theory": true,
    "source_type": "BAD",
    "audience_category": "party_member",
    "study_hours": null,
    "photo_count": 1,
    "participants": []
  }'

echo
echo "--- D) training_at 缺时间部分 ---"
curl -s -w '\nHTTP=%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_branch_id": 5,
    "training_at": "2026-07-26",
    "location": "测试",
    "theme": "主题",
    "participant_count": 1,
    "online_offline": "offline",
    "is_centralized": true,
    "is_innovation_theory": true,
    "source_type": "self_organize",
    "audience_category": "party_member",
    "study_hours": null,
    "photo_count": 1,
    "participants": []
  }'

echo
echo "--- E) organizer_branch_id=0 ---"
curl -s -w '\nHTTP=%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_branch_id": 0,
    "training_at": "2026-07-26T14:00:00",
    "location": "测试",
    "theme": "主题",
    "participant_count": 1,
    "online_offline": "offline",
    "is_centralized": true,
    "is_innovation_theory": true,
    "source_type": "self_organize",
    "audience_category": "party_member",
    "study_hours": null,
    "photo_count": 1,
    "participants": []
  }'
