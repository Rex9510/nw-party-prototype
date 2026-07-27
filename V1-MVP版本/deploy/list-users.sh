#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
sqlite3 -header -column "$DB" "SELECT id, phone, name, role, branch_id, community_id FROM users ORDER BY id;"
