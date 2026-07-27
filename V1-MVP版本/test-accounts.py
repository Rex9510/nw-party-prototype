"""快速验证所有种子账号都能登录 + me 拿到正确信息。"""
import json
import urllib.request


def http(method, url, body=None, token=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        return e.code, body


def login_and_me(phone, pwd):
    code, body = http("POST", "http://127.0.0.1:8000/api/v1/auth/login",
                      {"phone": phone, "password": pwd})
    if code != 200:
        return f"LOGIN FAIL ({code}): {body}"
    token = body["access_token"]
    code2, me = http("GET", "http://127.0.0.1:8000/api/v1/auth/me", token=token)
    if code2 != 200:
        return f"ME FAIL ({code2}): {me}"
    return f"OK  role={me['role']}  name={me['name']}"


print("=== 直接打 8000（不走 vite proxy）===")
for phone, pwd in [
    ("13800000000", "pass1234"),  # system admin
    ("13800000001", "pass1234"),  # street lead
    ("13800000002", "pass1234"),  # community org
    ("13800000003", "pass1234"),  # branch secretary
    ("13800000010", "pass1234"),  # member（党员）
    ("13800000000", "admin123"),  # 旧密码：应该 FAIL
    ("13800000010", "wrong"),     # 错密码：应该 FAIL
]:
    print(f"  {phone}/{pwd:10s} -> {login_and_me(phone, pwd)}")

print()
print("=== 走 vite proxy 5173 -> 8000 ===")
for phone, pwd in [
    ("13800000000", "pass1234"),
    ("13800000010", "pass1234"),
]:
    print(f"  {phone}/{pwd:10s} -> ", end="")
    try:
        code, body = http("POST", "http://127.0.0.1:5173/api/v1/auth/login",
                          {"phone": phone, "password": pwd})
        if code == 200:
            print(f"OK (got token len={len(body['access_token'])})")
        else:
            print(f"FAIL ({code}): {body}")
    except Exception as e:
        print(f"ERR: {e}")
