"""检查迁移后的数据是否正确。"""
import sqlite3
c = sqlite3.connect(r'E:\new party\nw-party-prototype\V1-MVP版本\nwparty_prod.db')

print('=== DDL ===')
for r in c.execute("SELECT sql FROM sqlite_master WHERE name = 'activities'"):
    print(r[0])

print()
print('=== ALL ROWS (raw) ===')
for r in c.execute('SELECT id, source_type, audience_category, typeof(audience_category), upper_org, study_methods, typeof(study_methods) FROM activities'):
    print(f'  id={r[0]} src={r[1]} aud={r[2]!r} (type={r[3]}) upper={r[4]!r} methods={r[5]!r} (type={r[6]})')

print()
print('=== alembic_version ===')
for r in c.execute('SELECT * FROM alembic_version'):
    print(f'  {r}')

c.close()
