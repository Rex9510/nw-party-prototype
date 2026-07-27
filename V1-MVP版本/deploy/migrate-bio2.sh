#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 备份 ---"
cp "$DB" "${DB}.bak.$(date +%H%M%S)"

echo
echo "--- 1) 加 lecturer_bio ---"
sqlite3 "$DB" "ALTER TABLE activities ADD COLUMN lecturer_bio TEXT;" 2>&1 || echo "(已存在)"

echo
echo "--- 2) 重建表让 study_hours 可空 ---"
sqlite3 "$DB" <<'SQL'
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE activities_new (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    organizer_branch_id INTEGER NOT NULL,
    community_id INTEGER NOT NULL,
    training_at DATETIME NOT NULL,
    location VARCHAR(255) NOT NULL,
    lecturer_name VARCHAR(64),
    lecturer_bio TEXT,
    theme VARCHAR(255) NOT NULL,
    participant_count INTEGER NOT NULL DEFAULT 0,
    online_offline VARCHAR(16) NOT NULL,
    is_centralized BOOLEAN NOT NULL,
    is_innovation_theory BOOLEAN NOT NULL,
    source_type VARCHAR(16) NOT NULL,
    audience_category VARCHAR(16) NOT NULL,
    study_hours NUMERIC(5, 1),
    status VARCHAR(16) NOT NULL DEFAULT 'draft',
    reject_reason TEXT,
    created_by INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(organizer_branch_id) REFERENCES branches(id),
    FOREIGN KEY(community_id) REFERENCES communities(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);
INSERT INTO activities_new SELECT
    id, organizer_branch_id, community_id, training_at, location,
    lecturer_name, lecturer_bio, theme, participant_count,
    online_offline, is_centralized, is_innovation_theory,
    source_type, audience_category, study_hours, status, reject_reason,
    created_by, created_at, updated_at
FROM activities;
DROP TABLE activities;
ALTER TABLE activities_new RENAME TO activities;
CREATE INDEX ix_activities_organizer_branch_id ON activities(organizer_branch_id);
CREATE INDEX ix_activities_community_id ON activities(community_id);
CREATE INDEX ix_activities_training_at ON activities(training_at);
CREATE INDEX ix_activities_status ON activities(status);
COMMIT;
PRAGMA foreign_keys=ON;
SQL

echo
echo "--- 验证：表结构 ---"
sqlite3 -header -column "$DB" "PRAGMA table_info(activities);" | grep -E "name|study_hours|lecturer"

echo
echo "--- 验证：数据完整性 ---"
sqlite3 -header -column "$DB" "SELECT id, theme, lecturer_name, lecturer_bio, study_hours FROM activities;"
