#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 所有引用 branch 1 的行（应该全部清空）---"
for tbl in members users activities activity_participants member_imports audit_flows audit_logs; do
  echo "  $tbl:"
  sqlite3 -header -column "$DB" "
    SELECT * FROM $tbl WHERE branch_id=1;
  " 2>/dev/null
  echo "  ---"
done
