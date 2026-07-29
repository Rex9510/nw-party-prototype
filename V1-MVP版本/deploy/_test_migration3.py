"""Test the v2 activity migration against local dev DB."""
import sqlite3
import json
import os
import shutil
import tempfile

prod_db = r'E:\new party\nw-party-prototype\V1-MVP版本\nwparty_local.db'
if not os.path.exists(prod_db):
    print('NO_LOCAL_DB')
    raise SystemExit(0)

tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
tmp.close()
shutil.copy2(prod_db, tmp.name)
c = sqlite3.connect(tmp.name)

print('=== BEFORE ===')
cols = [r[1] for r in c.execute('PRAGMA table_info(activities)').fetchall()]
print('cols:', cols)
print('row count:', c.execute('SELECT COUNT(*) FROM activities').fetchone()[0])
print()
print('sample audiences:')
for r in c.execute('SELECT id, source_type, audience_category FROM activities LIMIT 5').fetchall():
    print(' ', r)

# ============= 跑迁移 =============
print()
print('=== MIGRATING ===')

# 1) upper_org
try:
    c.execute('ALTER TABLE activities ADD COLUMN upper_org VARCHAR(50)')
    print('  + upper_org added')
except Exception as e:
    print('  upper_org err:', e)

# 2) study_methods
try:
    c.execute('ALTER TABLE activities ADD COLUMN study_methods JSON NOT NULL DEFAULT "[]"')
    print('  + study_methods added')
except Exception as e:
    print('  study_methods err:', e)

# 3) audience_category: String -> JSON
try:
    c.execute('ALTER TABLE activities ADD COLUMN audience_category_new JSON NOT NULL DEFAULT "[]"')
    print('  + audience_category_new added')
except Exception as e:
    print('  audience_category_new err:', e)

# 迁移数据
rows = c.execute('SELECT id, audience_category FROM activities').fetchall()
print(f'  migrating {len(rows)} rows')
for r in rows:
    aid, old = r
    if old is None or old == '':
        new = '[]'
    else:
        new = json.dumps([old], ensure_ascii=False)
    c.execute('UPDATE activities SET audience_category_new = ? WHERE id = ?', (new, aid))
print(f'  migrated {len(rows)} rows')

# 删旧列 + 改名
# SQLite 不支持 DROP COLUMN 老版本（3.35 之前），用 batch
# 简化：直接 CREATE 新表 + INSERT 新表 + DROP 老表 + ALTER RENAME
c.execute('ALTER TABLE activities RENAME TO activities_old')
c.execute('''
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    audience_category JSON NOT NULL,
    study_hours NUMERIC(5,1) NOT NULL,
    upper_org VARCHAR(50),
    study_methods JSON NOT NULL DEFAULT '[]',
    status VARCHAR(16) NOT NULL DEFAULT 'draft',
    reject_reason TEXT,
    created_by INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
''')
# 复制数据
c.execute('''
INSERT INTO activities (
    id, organizer_branch_id, community_id, training_at, location,
    lecturer_name, theme, participant_count,
    online_offline, is_centralized, is_innovation_theory, source_type,
    audience_category, study_hours, upper_org, study_methods,
    status, reject_reason, created_by, created_at, updated_at
)
SELECT
    id, organizer_branch_id, community_id, training_at, location,
    lecturer_name, theme, participant_count,
    online_offline, is_centralized, is_innovation_theory, source_type,
    audience_category_new, study_hours, upper_org, study_methods,
    status, reject_reason, created_by, created_at, updated_at
FROM activities_old
''')
c.execute('DROP TABLE activities_old')
print('  + table recreated with JSON audience_category')

# 占位 upper_send
ph_rows = c.execute("SELECT id, source_type FROM activities WHERE source_type = 'upper_send' AND (upper_org IS NULL OR upper_org = '')").fetchall()
for r in ph_rows:
    c.execute("UPDATE activities SET upper_org = '（待补充）' WHERE id = ?", (r[0],))
print(f'  + backfilled {len(ph_rows)} upper_send placeholders')

c.commit()

# ============= 验证 =============
print()
print('=== AFTER ===')
cols = [r[1] for r in c.execute('PRAGMA table_info(activities)').fetchall()]
print('cols:', cols)
print()
print('row count:', c.execute('SELECT COUNT(*) FROM activities').fetchone()[0])
print()
print('sample after:')
for r in c.execute('SELECT id, source_type, audience_category, upper_org, study_methods FROM activities LIMIT 8').fetchall():
    aid, src, aud, up, sm = r
    try:
        aud_disp = json.loads(aud) if isinstance(aud, str) else aud
    except Exception:
        aud_disp = aud
    try:
        sm_disp = json.loads(sm) if isinstance(sm, str) else sm
    except Exception:
        sm_disp = sm
    print(f'  id={aid} src={src} aud={aud_disp} upper_org={up!r} methods={sm_disp}')
print()
print('=== distinct audience values (flatten) ===')
seen = set()
for r in c.execute("SELECT audience_category FROM activities WHERE audience_category != '[]'").fetchall():
    try:
        arr = json.loads(r[0]) if isinstance(r[0], str) else r[0]
        for x in arr:
            seen.add(x)
    except Exception:
        pass
for v in sorted(seen):
    print(f'  {v!r}')

c.close()
os.unlink(tmp.name)
print('DONE (tmp cleaned)')
