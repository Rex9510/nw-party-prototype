#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 当前 activities ---"
sqlite3 -header -column "$DB" "SELECT id, theme, lecturer_name, lecturer_bio FROM activities;"
echo
echo "--- 找 branch_id=5 (刘海宝所在) ---"
sqlite3 -header -column "$DB" "SELECT id, name FROM branches WHERE id=5;"

echo
echo "--- 登录 ---"
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"13800000000","password":"pass1234"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
echo "TOKEN OK"

echo
echo "--- 创建活动（study_hours=null + lecturer_bio）---"
# 用刘海宝 (member_id=4) 作为参会人员
RESP=$(curl -s -X POST http://127.0.0.1:8000/api/v1/activities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organizer_branch_id": 5,
    "training_at": "2026-07-26T14:00:00",
    "location": "测试会议室",
    "lecturer_name": "王教授",
    "lecturer_bio": "清华大学马克思主义学院教授，长期从事党史党建研究。",
    "theme": "测试活动带讲师简介",
    "participant_count": 1,
    "online_offline": "offline",
    "is_centralized": true,
    "is_innovation_theory": true,
    "source_type": "self_organize",
    "audience_category": "party_member",
    "study_hours": null,
    "participants": [{"member_id": 4, "study_hours": 0}]
  }')
echo "raw: $RESP"
echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('id:', d.get('id'))
print('study_hours:', d.get('study_hours'))
print('lecturer_name:', d.get('lecturer_name'))
print('lecturer_bio:', d.get('lecturer_bio'))
"
