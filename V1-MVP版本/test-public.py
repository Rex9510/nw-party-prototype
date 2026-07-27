import urllib.request, json
# 不带 token
req = urllib.request.Request('http://localhost:8000/api/v1/public/members/3')
data = json.loads(urllib.request.urlopen(req).read())
print('Member:', data['member']['name'])
print('Branch:', data['member']['branch']['name'] if data['member']['branch'] else None)
print('Community:', data['member']['community']['name'] if data['member']['community'] else None)
print('Street:', data['member']['street']['name'] if data['member']['street'] else None)
print('Stats:', data['stats'])
print('Trainings count:', len(data['trainings']))
for t in data['trainings'][:3]:
    print('  -', t['theme'], '|', t['training_at'], '|', t['study_hours'], 'h | photos=', len(t['photos']))

# 不存在的 ID
req2 = urllib.request.Request('http://localhost:8000/api/v1/public/members/99999')
try:
    urllib.request.urlopen(req2)
except urllib.request.HTTPError as e:
    print('404 OK:', e.code)
