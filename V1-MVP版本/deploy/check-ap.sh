#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
sqlite3 -header -column "$DB" "SELECT * FROM activity_participants;"
echo
echo "--- FK list (谁引用 member) ---"
sqlite3 -header -column "$DB" "
SELECT m.name AS from_tbl, p.'from' AS col, fk.'table' AS ref_tbl, fk.'to' AS ref_col
FROM sqlite_master m, pragma_foreign_key_list(m.name) fk, pragma_table_info(m.name) p
WHERE fk.'table' = 'members' AND p.cid = fk.'from';
"
