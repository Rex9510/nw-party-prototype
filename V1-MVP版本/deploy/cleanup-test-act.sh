#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
sqlite3 "$DB" "DELETE FROM activity_participants WHERE activity_id=4; DELETE FROM activities WHERE id=4; SELECT id, theme FROM activities;"
