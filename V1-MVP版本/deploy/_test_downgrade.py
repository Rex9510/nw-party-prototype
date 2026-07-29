"""Test downgrade from 0003 back to 0002, then re-upgrade."""
import os
import sys
import sqlite3
import json
import shutil

prod_db = r'E:\new party\nw-party-prototype\V1-MVP版本\nwparty_prod.db'
backup_db = prod_db + '.downgrade_backup'

# Already at 0003 — save current state
if os.path.exists(backup_db):
    os.unlink(backup_db)
shutil.copy2(prod_db, backup_db)
print(f'pre-downgrade backup: {backup_db}')

# Run downgrade
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///' + prod_db.replace('\\', '/')

import subprocess
backend_dir = r'E:\new party\nw-party-prototype\V1-MVP版本\backend'
print('=== running alembic downgrade 2026_07_27_0002 ===')
r = subprocess.run(
    [sys.executable, '-m', 'alembic', 'downgrade', '2026_07_27_0002'],
    cwd=backend_dir, capture_output=True, text=True,
    env={**os.environ, 'DATABASE_URL': os.environ['DATABASE_URL']},
)
print('STDOUT:', r.stdout[:2000] if r.stdout else '(empty)')
print('STDERR:', r.stderr[:2000] if r.stderr else '(empty)')
print('returncode:', r.returncode)
if r.returncode != 0:
    print('!!! downgrade FAILED')
    shutil.copy2(backup_db, prod_db)
    sys.exit(1)

# Verify
print()
print('=== VERIFY downgrade ===')
c = sqlite3.connect(prod_db)
for r in c.execute('PRAGMA table_info(activities)'):
    print('  col:', r)
print()
for r in c.execute('SELECT id, source_type, audience_category, typeof(audience_category) FROM activities'):
    print(f'  id={r[0]} src={r[1]} aud={r[2]!r} type={r[3]}')
print()
print('alembic_version:', c.execute('SELECT * FROM alembic_version').fetchone())
c.close()

# Now re-upgrade
print()
print('=== re-upgrade back to head ===')
r2 = subprocess.run(
    [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
    cwd=backend_dir, capture_output=True, text=True,
    env={**os.environ, 'DATABASE_URL': os.environ['DATABASE_URL']},
)
print('STDOUT:', r2.stdout[:2000] if r2.stdout else '(empty)')
print('STDERR:', r2.stderr[:2000] if r2.stderr else '(empty)')
print('returncode:', r2.returncode)
if r2.returncode != 0:
    print('!!! re-upgrade FAILED')
    sys.exit(1)

print()
print('=== VERIFY re-upgrade ===')
c2 = sqlite3.connect(prod_db)
for r in c2.execute('PRAGMA table_info(activities)'):
    print('  col:', r)
print()
for r in c2.execute('SELECT id, source_type, audience_category, typeof(audience_category) FROM activities'):
    print(f'  id={r[0]} src={r[1]} aud={r[2]!r} type={r[3]}')
print()
print('alembic_version:', c2.execute('SELECT * FROM alembic_version').fetchone())
c2.close()

print()
print('ALL PASS')
