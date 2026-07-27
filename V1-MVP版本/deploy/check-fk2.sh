#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 1) 哪些表有外键引用 members ---"
sqlite3 -header -column "$DB" "
SELECT DISTINCT m.name AS from_table
FROM sqlite_master m, pragma_foreign_key_list(m.name) fk
WHERE fk.'table' = 'members';
"
echo
echo "--- 2) 这些表里 member_id=1..3 的记录数（看哪些引用了要删的 3 人）---"
for tbl in activity_participants audit_flows audit_logs study_hours; do
  echo "  $tbl:"
  sqlite3 -header -column "$DB" "
    SELECT member_id, COUNT(*) AS cnt FROM $tbl WHERE member_id IN (1,2,3) GROUP BY member_id;
  " 2>/dev/null || echo "    (no member_id column)"
done
