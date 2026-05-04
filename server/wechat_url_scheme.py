"""
微信小程序「方式二」URL Scheme：服务端调用 wxa/generatescheme。
文档：https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/qrcode-link/url-scheme/url-scheme/api_generatescheme.html

环境变量（必填 Secret 才能真实出链；i龙岗 AppId 默认见下方常量）：
  target=ilonggang：优先 WECHAT_ILG_APPID + WECHAT_ILG_SECRET，否则 WECHAT_MINI_APPID + WECHAT_MINI_SECRET；
  若未配置 AppId 则 i龙岗 使用内置公开 AppId wx201f04ef8f8d6b7c（须与微信后台一致）。
  其它 target：使用 WECHAT_MINI_APPID / WECHAT_MINI_SECRET。
可选：
  WECHAT_SCHEME_PATH / WECHAT_SCHEME_QUERY — 打开后落地路径与 query（如 pages/index/index）。
  WECHAT_ILG_SCHEME_PATH / WECHAT_ILG_SCHEME_QUERY — target=ilonggang 时优先于上面两项。
  WECHAT_SCHEME_EXPIRE_DAYS — 过期天数 1–30，默认 30。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

# i龙岗小程序 AppId（公开，与产品配置一致）
DEFAULT_ILONGGANG_APPID = "wx201f04ef8f8d6b7c"

_TOKEN_CACHE: dict = {}


def _get_access_token(appid: str, secret: str):
    if not appid or not secret:
        return None, "missing_appid_or_secret"
    now = time.time()
    slot = _TOKEN_CACHE.get(appid) or {}
    tok = slot.get("token") or ""
    exp = float(slot.get("exp") or 0)
    if tok and exp > now + 120:
        return tok, None
    q = urllib.parse.urlencode(
        {"grant_type": "client_credential", "appid": appid, "secret": secret}
    )
    url = "https://api.weixin.qq.com/cgi-bin/token?" + q
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"token_request_failed:{exc}"
    if data.get("errcode"):
        return None, data.get("errmsg") or str(data)
    access = data.get("access_token")
    if not access:
        return None, "no_access_token_in_response"
    _TOKEN_CACHE[appid] = {
        "token": access,
        "exp": now + float(data.get("expires_in") or 7200),
    }
    return access, None


def _credentials_for_target(target: str) -> tuple[str, str]:
    t = (target or "").strip()
    if t == "ilonggang":
        appid = (
            os.environ.get("WECHAT_ILG_APPID", "").strip()
            or os.environ.get("WECHAT_MINI_APPID", "").strip()
            or DEFAULT_ILONGGANG_APPID
        )
        secret = (
            os.environ.get("WECHAT_ILG_SECRET", "").strip()
            or os.environ.get("WECHAT_MINI_SECRET", "").strip()
        )
    else:
        appid = os.environ.get("WECHAT_MINI_APPID", "").strip()
        secret = os.environ.get("WECHAT_MINI_SECRET", "").strip()
    return appid, secret


def _scheme_body_for_target(target: str) -> dict:
    if target == "ilonggang":
        path = os.environ.get("WECHAT_ILG_SCHEME_PATH", os.environ.get("WECHAT_SCHEME_PATH", "")).strip()
        query = os.environ.get("WECHAT_ILG_SCHEME_QUERY", os.environ.get("WECHAT_SCHEME_QUERY", "")).strip()
    else:
        path = os.environ.get("WECHAT_SCHEME_PATH", "").strip()
        query = os.environ.get("WECHAT_SCHEME_QUERY", "").strip()
    try:
        days = int(os.environ.get("WECHAT_SCHEME_EXPIRE_DAYS", "30"))
    except ValueError:
        days = 30
    days = max(1, min(30, days))
    return {
        "jump_wxa": {"path": path, "query": query},
        "expire_type": 1,
        "expire_interval": days,
    }


def generate_url_scheme_for_target(target: str) -> dict:
    """
    返回 dict:
      成功: { "ok": True, "openlink": "weixin://...", "url_scheme": "weixin://..." }
      失败: { "ok": False, "errcode": int|str, "errmsg": str }
    """
    target = (target or "ilonggang").strip() or "ilonggang"
    appid, secret = _credentials_for_target(target)
    token, terr = _get_access_token(appid, secret)
    if not token:
        msg = terr or "token_error"
        if not secret and target == "ilonggang":
            msg = (
                msg
                + "（i龙岗需配置 WECHAT_ILG_SECRET 或 WECHAT_MINI_SECRET；AppId 已默认 "
                + DEFAULT_ILONGGANG_APPID
                + "）"
            )
        return {"ok": False, "errcode": -1, "errmsg": msg}

    body = _scheme_body_for_target(target)
    api = "https://api.weixin.qq.com/wxa/generatescheme?access_token=" + urllib.parse.quote(token, safe="")
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        api,
        data=raw,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            out = json.loads(e.read().decode("utf-8"))
        except Exception:
            out = {"errcode": e.code, "errmsg": e.reason or str(e)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "errcode": -2, "errmsg": str(exc)}

    ec = out.get("errcode")
    if ec not in (0, None):
        return {
            "ok": False,
            "errcode": ec,
            "errmsg": out.get("errmsg") or json.dumps(out, ensure_ascii=False),
        }
    openlink = (out.get("openlink") or "").strip()
    if not openlink:
        return {"ok": False, "errcode": -3, "errmsg": "no_openlink_in_wechat_response", "raw": out}
    return {"ok": True, "openlink": openlink, "url_scheme": openlink}
