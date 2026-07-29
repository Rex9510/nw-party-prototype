const { Client } = require('ssh2');
const fs = require('fs');
const conn = new Client();
conn.on('ready', () => {
  conn.exec(
    'chown nwparty:nwparty /var/log/nwparty/access.log /var/log/nwparty/error.log 2>/dev/null; '
    + 'pkill -f gunicorn 2>/dev/null; sleep 2; '
    + 'pm2 start nwparty-api 2>&1; echo "RESTART_OK"',
    (err, stream) => {
      if (err) { console.error('EXEC_ERR', err); conn.end(); process.exit(1); return; }
      let out = '';
      stream.on('data', (d) => { out += d.toString(); });
      stream.stderr.on('data', (d) => { out += '[STDERR]' + d.toString(); });
      stream.on('close', (code) => {
        conn.end();
        console.log('EXIT_CODE:', code);
        console.log('OUTPUT:', out);
      });
    },
  );
});
conn.on('error', (e) => { console.error('CONN_ERR', e); process.exit(1); });
conn.connect({
  host: '47.107.77.15', port: 22, username: 'root',
  privateKey: fs.readFileSync('C:\\Users\\rex.zhu\\.ssh\\rex_root.pem'),
});
