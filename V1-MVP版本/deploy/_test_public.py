"""验证公开页接口响应体大小"""
import urllib.request, json
import sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'http://127.0.0.1:8000/api/v1/public/members/7'
req = urllib.request.Request(url)
resp = urllib.request.urlopen(req, timeout=10)
body = resp.read()
print(f'Status: {resp.status}')
print(f'Body size: {len(body)} bytes ({len(body)/1024:.1f} KB)')
data = json.loads(body)
print(f'Member name: {data["member"]["name"]}')
print(f'Member photo_urls count: {len(data["member"]["photo_urls"])}')
print(f'Trainings count: {len(data["trainings"])}')
for t in data['trainings']:
    print(f'  Activity {t["activity_id"]} "{t["theme"][:30]}" attachments={len(t["attachments"])}')
    for a in t['attachments']:
        thumb_size = len(a.get('thumbnail_url') or '')
        print(f'    - id={a["id"]} kind={a["kind"]} is_image={a["is_image"]} thumb_size={thumb_size}B')
