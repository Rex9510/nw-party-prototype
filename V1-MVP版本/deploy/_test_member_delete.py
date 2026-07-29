"""Test delete member and create member with duplicate phone"""
import sys, json, os, urllib.request, urllib.error
sys.path.insert(0, '/var/www/nwparty/src/backend')
os.environ['JWT_SECRET'] = 'bJU0IISYL2PsI3w6qhH9vvHqDTF-iSdvmPvFi1jYfs1YZIQffj2j90waORLMscPt'
os.environ['JWT_ALGORITHM'] = 'HS256'
os.environ['ACCESS_TOKEN_EXPIRE_MINUTES'] = '10080'

from app.core.security import create_access_token
token = create_access_token(subject="1")
H = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# Test 1: Find an active member to test soft delete
import sqlite3
con = sqlite3.connect('/var/www/nwparty/data/nwparty.db')
cur = con.execute("select id, name, phone, status, branch_id from members where status='active' and id < 90 order by id limit 1")
m = cur.fetchone()
con.close()
if not m:
    print('NO active member found for test')
    sys.exit(1)
member_id, name, phone, _, branch_id = m
print(f'Test member: ID={member_id} name={name} phone={phone}')

# Test 1: Soft delete should work
print('\n=== Test 1: Soft delete (active -> dimission) ===')
req = urllib.request.Request(
    f'http://127.0.0.1:8000/api/v1/members/{member_id}',
    method='DELETE',
    headers={'Authorization': f'Bearer {token}'}
)
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print(f'  DELETE OK status={resp.status}')

    # verify
    con = sqlite3.connect('/var/www/nwparty/data/nwparty.db')
    cur = con.execute("select status from members where id=?", (member_id,))
    new_status = cur.fetchone()[0]
    con.close()
    print(f'  After delete: status={new_status} {"OK" if new_status == "dimission" else "FAIL"}')
except urllib.error.HTTPError as e:
    print(f'  HTTP ERROR {e.code}: {e.read().decode()[:200]}')
except Exception as e:
    print(f'  ERROR: {e}')

# Test 2: Try to soft-delete SAME phone again (should NOT conflict now with partial index)
print('\n=== Test 2: Create then delete same phone ===')
# Pick a different active member to delete first
con = sqlite3.connect('/var/www/nwparty/data/nwparty.db')
cur = con.execute("select id, name, phone, branch_id from members where status='active' and id != ? order by id limit 1", (member_id,))
m2 = cur.fetchone()
con.close()
if m2:
    mid2, name2, phone2, bid2 = m2
    print(f'  Will delete: ID={mid2} name={name2} phone={phone2}')

    req2 = urllib.request.Request(
        f'http://127.0.0.1:8000/api/v1/members/{mid2}',
        method='DELETE',
        headers={'Authorization': f'Bearer {token}'}
    )
    try:
        resp2 = urllib.request.urlopen(req2, timeout=10)
        print(f'  DELETE OK status={resp2.status}')

        # Now re-create member with same phone, then try to soft-delete again
        payload = json.dumps({
            "branch_id": bid2,
            "name": "重号测试",
            "phone": phone2,
            "status": "active",
        }).encode('utf-8')
        req3 = urllib.request.Request('http://127.0.0.1:8000/api/v1/members', data=payload, headers=H, method='POST')
        try:
            resp3 = urllib.request.urlopen(req3, timeout=10)
            new_id = json.loads(resp3.read())['id']
            print(f'  CREATE OK new_id={new_id} phone={phone2}')

            # Now try to soft-delete new one (should fail because old one is dimission with same phone, and partial index will catch it)
            req4 = urllib.request.Request(
                f'http://127.0.0.1:8000/api/v1/members/{new_id}',
                method='DELETE',
                headers={'Authorization': f'Bearer {token}'}
            )
            try:
                resp4 = urllib.request.urlopen(req4, timeout=10)
                print(f'  DELETE-2 OK status={resp4.status}')
                con = sqlite3.connect('/var/www/nwparty/data/nwparty.db')
                cur = con.execute("select status from members where id=?", (new_id,))
                print(f'  After delete-2: status={cur.fetchone()[0]}')
                con.close()
            except urllib.error.HTTPError as e:
                print(f'  DELETE-2 HTTP ERROR {e.code}: {e.read().decode()[:200]}')
        except urllib.error.HTTPError as e:
            print(f'  CREATE HTTP ERROR {e.code}: {e.read().decode()[:200]}')
    except urllib.error.HTTPError as e:
        print(f'  HTTP ERROR {e.code}: {e.read().decode()[:200]}')

# Test 3: Create member with EXISTING active phone should be rejected (with proper error)
print('\n=== Test 3: Create with duplicate active phone (should 400) ===')
con = sqlite3.connect('/var/www/nwparty/data/nwparty.db')
cur = con.execute("select phone from members where status='active' limit 1")
existing = cur.fetchone()
con.close()
if existing:
    payload = json.dumps({
        "branch_id": 5,
        "name": "重号测试",
        "phone": existing[0],
        "status": "active",
    }).encode('utf-8')
    req5 = urllib.request.Request('http://127.0.0.1:8000/api/v1/members', data=payload, headers=H, method='POST')
    try:
        resp5 = urllib.request.urlopen(req5, timeout=10)
        print(f'  FAIL: should have been 400, got {resp5.status}')
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f'  HTTP {e.code}: {body[:200]}')
        if e.code == 400 and '已存在' in body:
            print('  OK rejected as expected')
