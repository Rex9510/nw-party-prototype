"""测试创建 street/community/branch 三个级别的党员"""
import sys, os, urllib.request, json
sys.path.insert(0, '/var/www/nwparty/src/backend')
os.environ['JWT_SECRET'] = 'bJU0IISYL2PsI3w6qhH9vvHqDTF-iSdvmPvFi1jYfs1YZIQffj2j90waORLMscPt'
os.environ['JWT_ALGORITHM'] = 'HS256'

from app.core.security import create_access_token
token = create_access_token(subject="1")
H = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# 1) street 级别党员（注意手机号不能跟现有的 active 重）
tests = [
    {
        "label": "street 级别",
        "body": {
            "org_level": "street",
            "street_id": 1,
            "name": "测试-街道级党员",
            "phone": "13900000001",
        }
    },
    {
        "label": "community 级别",
        "body": {
            "org_level": "community",
            "community_id": 3,
            "name": "测试-社区级党员",
            "phone": "13900000002",
        }
    },
    {
        "label": "branch 级别（老用法）",
        "body": {
            "org_level": "branch",
            "branch_id": 8,
            "name": "测试-支部级党员",
            "phone": "13900000003",
        }
    },
]

for t in tests:
    print(f'=== {t["label"]} ===')
    body = json.dumps(t["body"]).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/api/v1/members', data=body, headers=H, method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        print(f'  status={resp.status} id={result["id"]} org_level={result["org_level"]}')
        print(f'  branch_id={result["branch_id"]} community_id={result["community_id"]} street_id={result["street_id"]}')
    except urllib.error.HTTPError as e:
        print(f'  HTTP {e.code}: {e.read().decode()[:200]}')
    print()

# 清理
import sqlite3
con = sqlite3.connect('/var/www/nwparty/data/nwparty.db')
con.execute("delete from users where phone in ('13900000001','13900000002','13900000003')")
con.execute("delete from members where phone in ('13900000001','13900000002','13900000003')")
con.commit()
con.close()
print('cleaned up')
