#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 哪些表有外键引用 branches ---"
sqlite3 -header -column "$DB" "
SELECT DISTINCT m.name AS from_table
FROM sqlite_master m, pragma_foreign_key_list(m.name) fk
WHERE fk.'table' = 'branches';
"
echo
echo "--- 这些表里 branch_id=1 的记录 ---"
for tbl in activity_participants activities member_imports users; do
  echo "  $tbl:"
  sqlite3 -header -column "$DB" "
    SELECT branch_id, COUNT(*) AS cnt FROM $tbl WHERE branch_id=1 GROUP BY branch_id;
  " 2>/dev/null || echo "    (no branch_id column)"
done
