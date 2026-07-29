const { Client } = require('ssh2');
const fs = require('fs');
const conn = new Client();
const cmd = `bash -c "
echo '=== running process ==='
ps aux | grep -E 'gunicorn|uvicorn|nwparty' | grep -v grep | head -5
echo
echo '=== /api/v1/orgs/streets ==='
curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8000/api/v1/orgs/streets
echo
echo '=== /api/v1/orgs/branches/1/move-up (POST) ==='
curl -s -o /tmp/resp.txt -w '%{http_code}\\n' -X POST http://127.0.0.1:8000/api/v1/orgs/branches/1/move-up
cat /tmp/resp.txt
echo
echo '=== /api/v1/orgs/branches/1/move-up (GET, expect 405) ==='
curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8000/api/v1/orgs/branches/1/move-up
echo
echo '=== check routes in running code ==='
grep -n 'move-up' /var/www/nwparty/src/backend/app/api/v1/orgs.py | head -10
"`;
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    if (err) { console.error(err); return; }
    let out = '';
    stream.on('data', d => out += d);
    stream.stderr.on('data', d => out += d);
    stream.on('close', () => { console.log(out); conn.end(); });
  });
});
conn.on('error', e => console.error('CONN_ERR', e.message));
conn.connect({
  host: '47.107.77.15', port: 22, username: 'root',
  privateKey: fs.readFileSync('C:/Users/rex.zhu/.ssh/rex_root.pem'),
});
