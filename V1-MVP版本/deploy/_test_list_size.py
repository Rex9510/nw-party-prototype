"""Test members list response size"""
import sys, os, urllib.request, json
sys.path.insert(0, '/var/www/nwparty/src/backend')
os.environ['JWT_SECRET'] = 'bJU0IISYL2PsI3w6qhH9vvHqDTF-iSdvmPvFi1jYfs1YZIQffj2j90waORLMscPt'
os.environ['JWT_ALGORITHM'] = 'HS256'
os.environ['ACCESS_TOKEN_EXPIRE_MINUTES'] = '10080'

from app.core.security import create_access_token
token = create_access_token(subject="1")

for page in [1, 2, 5]:
    url = f'http://127.0.0.1:8000/api/v1/members?page={page}&page_size=20'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    resp = urllib.request.urlopen(req, timeout=10)
    body = resp.read()
    print(f'page={page} bytes={len(body)} status={resp.status}')
    if page == 1:
        data = json.loads(body)
        if data.get('items'):
            first = data['items'][0]
            print(f'  first item keys: {list(first.keys())}')
            print(f'  has photo_urls: {"photo_urls" in first}')
