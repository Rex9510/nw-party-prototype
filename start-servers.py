"""本地静态服务（项目根）+ 微信小程序 URL Scheme 接口（方案二）。

默认端口 8080。静态页与接口同源，便于 mobile_v2 使用 /api/wechat/url-scheme。

环境变量见 server/env.example.txt；至少配置 WECHAT_MINI_APPID、WECHAT_MINI_SECRET 后接口才会向微信要真实 openlink。
"""
import http.server
import json
import mimetypes
import os
import socketserver
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8080"))

mimetypes.add_type("text/babel", ".jsx")
socketserver.TCPServer.allow_reuse_address = True


class DevHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if not self.path.startswith("/api/"):
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        if self.path.split("?", 1)[0] == "/api/wechat/url-scheme":
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/wechat/url-scheme":
            self._handle_wechat_url_scheme(parsed.query)
            return
        super().do_GET()

    def _handle_wechat_url_scheme(self, query: str):
        try:
            from server import wechat_url_scheme as wus
        except ImportError as exc:
            body = {"ok": False, "errcode": -9, "errmsg": f"import_server_module_failed:{exc}"}
            self._send_json(500, body)
            return

        qs = urllib.parse.parse_qs(query)
        target = (qs.get("target") or ["ilonggang"])[0].strip() or "ilonggang"
        # url / shortlink 由前端传入便于日志与扩展；当前生成逻辑不依赖短链内容
        result = wus.generate_url_scheme_for_target(target)
        code = 200 if result.get("ok") else 503
        self._send_json(code, result)

    def _send_json(self, status: int, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    os.chdir(ROOT)
    with socketserver.TCPServer(("", PORT), DevHandler) as httpd:
        base = f"http://127.0.0.1:{PORT}"
        print(f"本地服务: {base}")
        print(f"  PC 管理端: {base}/pc-admin/login.html")
        print(f"  移动原型:  {base}/prototype/mobile_v2.html")
        print(f"  URL Scheme 接口: {base}/api/wechat/url-scheme?target=ilonggang&url=<当前页>")
        print("  配置 WECHAT_MINI_APPID / WECHAT_MINI_SECRET 后生效（见 server/env.example.txt）。")
        print("按 Ctrl+C 停止。")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
