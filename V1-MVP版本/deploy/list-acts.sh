#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
sqlite3 -header -column "$DB" "SELECT id, theme, status, study_hours FROM activities ORDER BY id DESC LIMIT 3;"
