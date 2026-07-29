import sqlite3
c = sqlite3.connect(r'E:\new party\nw-party-prototype\V1-MVP版本\nwparty_local.db')
for r in c.execute("SELECT sql FROM sqlite_master WHERE name = 'activities'").fetchall():
    print(r[0])
