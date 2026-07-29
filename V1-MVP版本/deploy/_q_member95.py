import sqlite3
conn = sqlite3.connect(r'/var/www/nwparty/data/nwparty.db')
print('=== members.phone=15812869715 ===')
for r in conn.execute("SELECT id, name, phone, status, org_level, branch_id, community_id, street_id, roles, identities FROM members WHERE phone='15812869715'"):
    print(r)
print('=== users.phone=15812869715 ===')
for r in conn.execute("SELECT id, phone, role, community_id, branch_id, street_id, status FROM users WHERE phone='15812869715'"):
    print(r)
