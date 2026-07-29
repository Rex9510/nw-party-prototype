import sqlite3
c = sqlite3.connect(r'E:\new party\nw-party-prototype\V1-MVP版本\nwparty_prod.db')
print('=== activities DDL ===')
for r in c.execute("SELECT sql FROM sqlite_master WHERE name = 'activities'"):
    print(r[0])
print()
print('=== indexes ===')
for r in c.execute("SELECT sql FROM sqlite_master WHERE name LIKE '%activities%' AND type='index'"):
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
print('=== sample data (5) ===')
for r in c.execute('SELECT id, source_type, audience_category, study_hours FROM activities LIMIT 5'):
    print(r)
c.close()
