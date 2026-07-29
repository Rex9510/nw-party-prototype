"""Test the v2 activity migration against PROD DB copy."""
import sqlite3
import json
import os

prod_db = r'E:\new party\nw-party-prototype\V1-MVP版本\nwparty_prod.db'
c = sqlite3.connect(prod_db)

print('=== BEFORE ===')
cols = [r[1] for r in c.execute('PRAGMA table_info(activities)').fetchall()]
print('cols:', cols)
print()
rows = c.execute('SELECT id, source_type, audience_category FROM activities').fetchall()
print(f'activities: {len(rows)} rows')
for r in rows:
    print(' ', r)
print()
fk_count = c.execute("SELECT COUNT(*) FROM activities WHERE source_type='upper_send'").fetchone()[0]
print(f'upper_send rows: {fk_count}')

c.close()
print('DONE')
