#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- activity_participants member_id IN (1,2,3) ---"
sqlite3 -header -column "$DB" "SELECT * FROM activity_participants WHERE member_id IN (1,2,3);"
echo
echo "--- study_hours member_id IN (1,2,3) ---"
sqlite3 -header -column "$DB" "SELECT * FROM study_hours WHERE member_id IN (1,2,3);"
echo
echo "--- 所有引用 branch_id=1 的可能表 ---"
for tbl in activity_participants activities member_imports users members; do
  cnt=$(sqlite3 "$DB" "SELECT COUNT(*) FROM $tbl WHERE branch_id=1;" 2>/dev/null)
  echo "$tbl: $cnt"
done
echo
echo "--- members 中 branch_id=1 的 ---"
sqlite3 "$DB" "SELECT id,name,status FROM members WHERE branch_id=1;"
echo
echo "--- study_hours member_id=1,2 ---"
sqlite3 -header -column "$DB" "SELECT * FROM study_hours WHERE member_id IN (1,2,3);"
