import sqlite3
conn = sqlite3.connect(r'/var/www/nwparty/data/nwparty.db')
print('=== users.role=branch_secretary (active) ===')
n = 0
for r in conn.execute("SELECT id, phone, role, community_id, branch_id, street_id, status FROM users WHERE role='branch_secretary' AND status='active' ORDER BY id"):
    print(r)
    n += 1
print(f'total active branch_secretary users: {n}')
print()
print('=== members.roles 包含 branch_secretary 的（active） ===')
n = 0
for r in conn.execute("SELECT id, name, phone, status, org_level, branch_id, community_id, street_id, roles FROM members WHERE status='active' AND roles LIKE '%branch_secretary%' ORDER BY id"):
    print(r)
    n += 1
print(f'total active members with roles containing branch_secretary: {n}')
