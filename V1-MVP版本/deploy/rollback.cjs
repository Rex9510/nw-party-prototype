// rollback-frontend.cjs
const { Client } = require('ssh2');
const fs = require('fs');

const CFG = {
  sshKey: process.env.SSH_KEY_PATH || 'C:\\Users\\rex.zhu\\.ssh\\rex_root.pem',
  sshUser: 'root',
  sshHost: '47.107.77.15',
  remoteDist: '/var/www/nwparty/frontend/dist',
  backupRoot: '/var/backups/nwparty/dist',
};

function sh(cmd) {
  return new Promise((resolve, reject) => {
    const conn = new Client();
    conn.on('ready', () => {
      conn.exec(cmd, (err, stream) => {
        if (err) { conn.end(); return reject(err); }
        let out = '', errOut = '';
        stream.on('data', d => out += d.toString('utf-8'));
        stream.stderr.on('data', d => errOut += d.toString('utf-8'));
        stream.on('close', (code) => {
          conn.end();
          if (code === 0) resolve({ stdout: out, stderr: errOut });
          else reject(new Error('exit=' + code + '\nSTDOUT: ' + out + '\nSTDERR: ' + errOut));
        });
      });
    });
    conn.on('error', reject);
    conn.connect({
      host: CFG.sshHost, port: 22, username: CFG.sshUser,
      privateKey: fs.readFileSync(CFG.sshKey),
    });
  });
}

(async () => {
  const ts = process.argv[2];
  if (!ts) {
    console.log('available backups (latest 10):');
    const r = await sh('ls -1t ' + CFG.backupRoot + ' 2>/dev/null | head -10 | nl');
    console.log(r.stdout);
    console.log();
    console.log('usage: node rollback.cjs <timestamp>');
    process.exit(1);
  }
  const remoteBackup = CFG.backupRoot + '/' + ts;
  const check = await sh('if [ -d ' + remoteBackup + ' ]; then echo OK; else echo MISSING; fi');
  if (!check.stdout.includes('OK')) {
    console.error('backup not found: ' + remoteBackup);
    process.exit(1);
  }

  console.log('rolling back to ' + ts + ' (' + remoteBackup + ')');
  const newTs = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 15);
  const preBackup = CFG.backupRoot + '/pre-rollback-' + newTs;

  console.log('[1/3] backup current remote');
  await sh('cp -r ' + CFG.remoteDist + ' ' + preBackup + ' && echo PRE_BACKUP_OK');

  console.log('[2/3] overwrite remote dist');
  await sh('rm -rf ' + CFG.remoteDist + ' && cp -r ' + remoteBackup + ' ' + CFG.remoteDist + ' && chown -R nwparty:nwparty ' + CFG.remoteDist + ' 2>/dev/null || true && echo ROLLBACK_OK');

  console.log('[3/3] verify');
  const r = await sh('curl -sI http://127.0.0.1:8081/ | head -3');
  console.log(r.stdout);
  if (!r.stdout.includes('200')) {
    console.error('nginx did not return 200 after rollback');
    process.exit(1);
  }

  console.log();
  console.log('============================================================');
  console.log('  frontend rollback OK');
  console.log('  current: ' + ts);
  console.log('  pre-rollback snapshot: ' + preBackup);
  console.log('============================================================');
})().catch(e => {
  console.error('FAIL:', e.message);
  process.exit(1);
});
