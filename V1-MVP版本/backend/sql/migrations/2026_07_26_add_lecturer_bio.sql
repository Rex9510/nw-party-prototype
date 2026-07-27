-- 2026-07-26: 培训活动讲师简介 + 学时改为可空
-- SQLite 不能直接 ALTER NOT NULL，需要重建表（这里用最稳的方式：新建临时表 → 拷数据 → 替换）
-- 幂等：列已存在时报错可忽略

-- 1) 加 lecturer_bio
ALTER TABLE activities ADD COLUMN lecturer_bio TEXT;

-- 2) study_hours NOT NULL -> NULLABLE
--    SQLite 改 NOT NULL 只能重建表，这里用 12-step 标准做法：
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
    study_hours NUMERIC(5, 1),  -- 改为可空
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
