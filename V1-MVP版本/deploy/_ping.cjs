const { Client } = require('ssh2');
const fs = require('fs');
const conn = new Client();
conn.on('ready', () => {
  conn.exec('echo HELLO_WORLD', (err, stream) => {
    if (err) { console.error('EXEC_ERR:', err.message); conn.end(); process.exit(1); return; }
    let out = '';
    stream.on('data', (d) => { out += d.toString(); });
    stream.stderr.on('data', (d) => { out += '[STDERR]' + d.toString(); });
    stream.on('close', (code, signal) => {
      console.log('CLOSE code:', code, 'signal:', signal);
      console.log('OUTPUT:', JSON.stringify(out));
      conn.end();
    });
  });
});
conn.on('error', (e) => { console.error('CONN_ERR:', e.message); process.exit(1); });
conn.connect({
  host: '47.107.77.15', port: 22, username: 'root',
  privateKey: fs.readFileSync('C:\\Users\\rex.zhu\\.ssh\\rex_root.pem'),
});
