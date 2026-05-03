import http.server, socketserver, os, mimetypes

mimetypes.add_type('text/babel', '.jsx')

os.chdir(r'D:/项目/党组织项目/prototype')

socketserver.TCPServer.allow_reuse_address = True

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

with socketserver.TCPServer(('127.0.0.1', 8888), Handler) as httpd:
    print('Mini-program serving at http://127.0.0.1:8888', flush=True)
    httpd.serve_forever()
