const { Client } = require('ssh2');
const fs = require('fs');
const path = require('path');

function withConn(fn) {
  return new Promise((resolve, reject) => {
    const conn = new Client();
    conn.on('ready', async () => {
      try { const r = await fn(conn); conn.end(); resolve(r); }
      catch (e) { conn.end(); reject(e); }
    });
    conn.on('error', reject);
    conn.connect({
      host: '47.107.77.15', port: 22, username: 'root',
      privateKey: fs.readFileSync('C:/Users/rex.zhu/.ssh/rex_root.pem'),
    });
  });
}

function shCmd(conn, cmd) {
  return new Promise((resolve, reject) => {
    conn.exec(cmd, (err, stream) => {
      if (err) { return reject(err); }
      let out = '';
      stream.on('data', d => out += d);
      stream.on('close', () => resolve(out));
    });
  });
}

(async () => {
  const localPath = path.resolve(__dirname, '..', 'nwparty_prod_copy.db');
  const r = await withConn(async (conn) => {
    return await shCmd(conn, `python3 -c "import sqlite3; c=sqlite3.connect('/var/www/nwparty/data/nwparty.db'); c.backup(open(r'${localPath.replace(/\\\\/g, '/').replace(/'/g, "\\'")}', 'wb').write if False else __import__('builtins').open(r'${localPath.replace(/\\\\/g, '/').replace(/'/g, "\\'")}', 'wb').write)" 2>&1 || true; ls -la ${localPath}"`);
  });
  console.log(r);
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
