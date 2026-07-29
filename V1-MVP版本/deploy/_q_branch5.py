import sqlite3
conn = sqlite3.connect(r'/var/www/nwparty/data/nwparty.db')
print('=== branch_id=5 (status=active) ===')
n = 0
for r in conn.execute("SELECT id, name, status, org_level, branch_id, community_id FROM members WHERE branch_id=5 AND status='active' ORDER BY id"):
    print(r)
    n += 1
print(f'total active: {n}')
print()
print('=== branch_id=5 (any status) ===')
n = 0
for r in conn.execute("SELECT id, name, status FROM members WHERE branch_id=5 ORDER BY id"):
    print(r)
    n += 1
print(f'total: {n}')
print()
print('=== branch_id=5 OR community_id=3 (org_level=community, status=active) ===')
n = 0
for r in conn.execute("SELECT id, name, status, org_level, branch_id, community_id FROM members WHERE status='active' AND (branch_id=5 OR (org_level='community' AND community_id=3)) ORDER BY id"):
    print(r)
    n += 1
print(f'total: {n}')
