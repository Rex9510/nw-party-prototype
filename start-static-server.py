"""本地静态服务（项目根）— 多线程版，避免 http.server 单线程卡死。

端口 8080。PC 管理端 / 小程序原型同源。
"""
import http.server
import os
import socketserver
from functools import partial

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8080"))

os.chdir(ROOT)
socketserver.TCPServer.allow_reuse_address = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        # 简化日志，方便在文件里 grep
        super().log_message(fmt, *args)


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    base = f"http://127.0.0.1:{PORT}"
    print(f"本地服务: {base}")
    print(f"  PC 管理端: {base}/pc-admin/login.html")
    print(f"  移动原型:  {base}/prototype/mobile_v2.html")
    print("按 Ctrl+C 停止。")
    with ThreadedServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()