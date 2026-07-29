"""Run alembic upgrade head against prod DB copy to validate migration."""
import os
import sys
import sqlite3

# 1) Backup prod copy
prod_db = r'E:\new party\nw-party-prototype\V1-MVP版本\nwparty_prod.db'
backup_db = prod_db + '.backup'
if os.path.exists(backup_db):
    os.unlink(backup_db)
import shutil
shutil.copy2(prod_db, backup_db)
print(f'backup: {backup_db}')

# 2) Set DATABASE_URL to point to prod copy
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///' + prod_db.replace('\\', '/')

# 3) Run alembic
import subprocess
backend_dir = r'E:\new party\nw-party-prototype\V1-MVP版本\backend'
print('=== running alembic upgrade head ===')
r = subprocess.run(
    [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
    cwd=backend_dir,
    capture_output=True, text=True, env={**os.environ, 'DATABASE_URL': os.environ['DATABASE_URL']},
)
print('STDOUT:')
print(r.stdout)
print('STDERR:')
print(r.stderr)
print('returncode:', r.returncode)
if r.returncode != 0:
    print('!!! migration failed')
    # restore
    shutil.copy2(backup_db, prod_db)
    print('restored from backup')
    sys.exit(1)

# 4) Verify
print()
print('=== VERIFY ===')
c = sqlite3.connect(prod_db)
cols = [r[1] for r in c.execute('PRAGMA table_info(activities)').fetchall()]
print('cols:', cols)
print()
rows = c.execute('SELECT id, source_type, audience_category, upper_org, study_methods FROM activities').fetchall()
print('activities after:')
for r in rows:
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
print('alembic_version:')
for r in c.execute('SELECT * FROM alembic_version').fetchall():
    print(' ', r)

c.close()
print('DONE')
