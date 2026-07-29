import sqlite3
c = sqlite3.connect(r'E:\new party\nw-party-prototype\V1-MVP版本\nwparty_prod_fresh.db')
print('=== activities DDL ===')
for r in c.execute("SELECT sql FROM sqlite_master WHERE name = 'activities'"):
    print(r[0])
print()
print('=== alembic_version ===')
for r in c.execute('SELECT * FROM alembic_version'):
    print(r)
print()
print('=== PRAGMA cols ===')
for r in c.execute('PRAGMA table_info(activities)'):
    print(r)
print()
print('=== sample (5) ===')
for r in c.execute('SELECT id, source_type, audience_category FROM activities LIMIT 5'):
    print(r)
c.close()
