#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
sqlite3 "$DB" "PRAGMA table_info(activity_participants);"
