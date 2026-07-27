#!/usr/bin/env bash
DB=/var/www/nwparty/data/nwparty.db
echo "--- 备份 ---"
cp "$DB" "${DB}.bak.$(date +%H%M%S)"

echo
echo "--- 重建表让 study_hours 可空 ---"
sqlite3 "$DB" <<'SQL'
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE activity_participants_new (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    study_hours NUMERIC(5, 1),
    attendance_status VARCHAR(16) NOT NULL DEFAULT 'signed',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(activity_id, member_id),
    FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    FOREIGN KEY(member_id) REFERENCES members(id)
);
INSERT INTO activity_participants_new SELECT
    id, activity_id, member_id, study_hours, attendance_status, created_at
FROM activity_participants;
DROP TABLE activity_participants;
ALTER TABLE activity_participants_new RENAME TO activity_participants;
CREATE INDEX ix_activity_participants_activity_id ON activity_participants(activity_id);
CREATE INDEX ix_activity_participants_member_id ON activity_participants(member_id);
COMMIT;
PRAGMA foreign_keys=ON;
SQL

echo
echo "--- 验证：表结构 ---"
sqlite3 -header -column "$DB" "PRAGMA table_info(activity_participants);" | grep -E "name|study_hours"

echo
echo "--- 验证：数据 ---"
sqlite3 -header -column "$DB" "SELECT id, activity_id, member_id, study_hours FROM activity_participants ORDER BY id DESC LIMIT 3;"
