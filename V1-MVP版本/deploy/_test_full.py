"""测试 /public/attachments/{id}/full 接口"""
import urllib.request, sys

# 测试 4 个 photo
for att_id in [1, 5, 6, 7]:
    url = f'http://127.0.0.1:8000/api/v1/public/attachments/{att_id}/full'
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=10)
        body = resp.read()
        print(f'attachment {att_id}: status={resp.status} bytes={len(body)} mime={resp.headers.get("Content-Type", "?")}')
    except Exception as e:
        print(f'attachment {att_id}: ERROR {e}')

# 测试非 photo（signin）
url = f'http://127.0.0.1:8000/api/v1/public/attachments/8/full'
try:
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=10)
    body = resp.read()
    print(f'attachment 8 (signin): status={resp.status} bytes={len(body)} mime={resp.headers.get("Content-Type", "?")}')
except Exception as e:
    print(f'attachment 8: ERROR {e}')
