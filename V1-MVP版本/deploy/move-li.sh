#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- before ---"
sqlite3 -header -column "$DB" "SELECT id, phone, name, role, community_id, branch_id FROM users WHERE id=3;"
echo
echo "--- update ---"
sqlite3 "$DB" "UPDATE users SET community_id=3 WHERE id=3;"
echo
echo "--- after ---"
sqlite3 -header -column "$DB" "SELECT id, phone, name, role, community_id, branch_id FROM users WHERE id=3;"
