"""直接打 API 看 500 的真正错误。"""
import urllib.request
import json
import ssl

# 1. 登录
login = urllib.request.Request(
    "http://localhost:8000/api/v1/auth/login",
    data=json.dumps({"phone": "13800000000", "password": "pass1234"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    r = urllib.request.urlopen(login, timeout=5)
    token = json.loads(r.read())["access_token"]
    print("login OK, token len:", len(token))
except Exception as e:
    print("login fail:", e)
    raise

# 2. 拉 list
get_req = urllib.request.Request(
    "http://localhost:8000/api/v1/members?page=1&page_size=5",
    headers={"Authorization": f"Bearer {token}"},
)
try:
    r = urllib.request.urlopen(get_req, timeout=5)
    data = json.loads(r.read())
    print("list OK, items:", len(data.get("items", [])))
    if data.get("items"):
        m = data["items"][0]
        print("first item roles type:", type(m.get("roles")).__name__, "value:", m.get("roles"))
        print("first item identities type:", type(m.get("identities")).__name__, "value:", m.get("identities"))
except urllib.error.HTTPError as e:
    print("list HTTPError:", e.code, e.read().decode()[:500])
except Exception as e:
    print("list fail:", e)
