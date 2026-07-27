#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
sqlite3 -header -column "$DB" "SELECT id, theme, lecturer_name, lecturer_bio, location, online_offline, is_centralized, is_innovation_theory, source_type, audience_category, study_hours, status FROM activities WHERE id=13;"
