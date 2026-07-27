"""SQLite 手动迁移：给 members 表加 roles / identities 列。"""
import sqlite3

db = r'D:\项目\党组织项目\V1-MVP版本\nwparty_local.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# 幂等：先查有没有
cur.execute("PRAGMA table_info(members)")
existing = {row[1] for row in cur.fetchall()}

added = []
if 'roles' not in existing:
    cur.execute("ALTER TABLE members ADD COLUMN roles TEXT")
    added.append('roles')
if 'identities' not in existing:
    cur.execute("ALTER TABLE members ADD COLUMN identities TEXT")
    added.append('identities')

conn.commit()

print('已加列:', added if added else '（都已存在，无需操作）')

# 复查
cur.execute("PRAGMA table_info(members)")
print('更新后 members 结构:')
for r in cur.fetchall():
    print(' -', r[1], r[2])

conn.close()
