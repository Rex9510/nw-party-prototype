const { Client } = require('ssh2');
const fs = require('fs');

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
  const r = await withConn(async (conn) => {
    return await shCmd(conn, `python3 << 'PYEOF'
import sqlite3
c = sqlite3.connect('/var/www/nwparty/data/nwparty.db')
for r in c.execute("SELECT sql FROM sqlite_master WHERE name = 'activities'").fetchall():
    print(r[0])
print()
print('=== sample ===')
for r in c.execute("SELECT id, source_type, audience_category FROM activities LIMIT 5").fetchall():
    print(' ', r)
print()
print('row count:', c.execute('SELECT COUNT(*) FROM activities').fetchone()[0])
print('upper_send count:', c.execute("SELECT COUNT(*) FROM activities WHERE source_type='upper_send'").fetchone()[0])
PYEOF`);
  });
  console.log(r);
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
