#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 所有草稿活动（status='draft'）---"
sqlite3 -header -column "$DB" "SELECT id, theme, lecturer_name, lecturer_bio, online_offline, is_centralized, is_innovation_theory, source_type, audience_category, study_hours FROM activities WHERE status='draft';"
echo
echo "--- 活动附件 ---"
sqlite3 -header -column "$DB" "SELECT id, activity_id, kind FROM activity_attachments;"
echo
echo "--- 参加人员 ---"
sqlite3 -header -column "$DB" "SELECT id, activity_id, member_id, study_hours FROM activity_participants;"
