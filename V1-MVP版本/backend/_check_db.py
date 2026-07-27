import sqlite3
db = r'D:\项目\党组织项目\V1-MVP版本\nwparty_local.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("PRAGMA table_info(members)")
print('members 表结构:')
for r in cur.fetchall():
    print(' -', r)
print()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('所有表:', [r[0] for r in cur.fetchall()])
conn.close()
