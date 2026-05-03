"""本地静态服务：项目根为站点根，单端口 8080。"""
import http.server
import mimetypes
import os
import socketserver

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8080

mimetypes.add_type("text/babel", ".jsx")
socketserver.TCPServer.allow_reuse_address = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def main():
    os.chdir(ROOT)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        base = f"http://127.0.0.1:{PORT}"
        print(f"本地服务: {base}")
        print(f"  PC 管理端: {base}/pc-admin/login.html")
        print(f"  原型目录:  {base}/prototype/")
        print("按 Ctrl+C 停止。")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
