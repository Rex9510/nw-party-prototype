"""测试 list_members 现在包含 community_id/street_id/org_level 字段"""
import sys, os, urllib.request, json
sys.path.insert(0, '/var/www/nwparty/src/backend')
os.environ['JWT_SECRET'] = 'bJU0IISYL2PsI3w6qhH9vvHqDTF-iSdvmPvFi1jYfs1YZIQffj2j90waORLMscPt'
os.environ['JWT_ALGORITHM'] = 'HS256'

from app.core.security import create_access_token
token = create_access_token(subject="1")

url = 'http://127.0.0.1:8000/api/v1/members?page=1&page_size=3'
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())
print(f'total: {data["total"]}')
for m in data['items']:
    print(f'  id={m["id"]} name={m["name"]} org_level={m.get("org_level")} branch_id={m.get("branch_id")} community_id={m.get("community_id")} street_id={m.get("street_id")}')
    print(f'    branch_name={m.get("branch_name")} community_name={m.get("community_name")} street_name={m.get("street_name")}')
