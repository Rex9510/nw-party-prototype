"""检查 members 和 users 状态。"""
import sqlite3
db = r'D:\项目\党组织项目\V1-MVP版本\nwparty_local.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
print('===== members 表 =====')
cur.execute("SELECT id, name, phone, roles, identities FROM members ORDER BY id DESC LIMIT 8")
for r in cur.fetchall():
    print(r)
print()
print('===== users 表 =====')
cur.execute("SELECT id, phone, name, role FROM users WHERE phone IN ('13553876377','15812869715','13900008888')")
for r in cur.fetchall():
    print(r)
conn.close()
