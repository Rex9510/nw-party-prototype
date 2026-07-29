// publish-frontend.cjs
// Push frontend dist to Aliyun
const { Client } = require('ssh2');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const CFG = {
  sshKey: process.env.SSH_KEY_PATH || 'C:\\Users\\rex.zhu\\.ssh\\rex_root.pem',
  sshUser: 'root',
  sshHost: '47.107.77.15',
  remoteDist: '/var/www/nwparty/frontend/dist',
  backupRoot: '/var/backups/nwparty/dist',
  localDist: path.resolve(__dirname, '..', 'frontend', 'dist'),
};

const TIMESTAMP = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 15);
const REMOTE_BACKUP = `${CFG.backupRoot}/${TIMESTAMP}`;

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
  console.log('============================================================');
  console.log('  nwparty frontend publish');
  console.log('============================================================');
  console.log('local:  ' + CFG.localDist);
  console.log('remote: ' + CFG.remoteDist);
  console.log('backup: ' + REMOTE_BACKUP);
  console.log();

  if (!fs.existsSync(CFG.localDist)) throw new Error('local dist missing: ' + CFG.localDist);
  if (!fs.existsSync(path.join(CFG.localDist, 'index.html'))) throw new Error('local dist missing index.html');
  if (!fs.existsSync(CFG.sshKey)) throw new Error('SSH key missing: ' + CFG.sshKey);

  console.log('[1/4] backup current remote dist');
  await sh('mkdir -p ' + CFG.backupRoot + ' && if [ -d ' + CFG.remoteDist + ' ]; then cp -r ' + CFG.remoteDist + ' ' + REMOTE_BACKUP + '; else mkdir -p ' + REMOTE_BACKUP + '; fi && echo BACKUP_OK');
  console.log('    OK');

  console.log('[2/4] upload new dist');
  await sh('rm -rf ' + CFG.remoteDist + ' && mkdir -p ' + CFG.remoteDist);
  const cmd = 'scp -i "' + CFG.sshKey + '" -o StrictHostKeyChecking=no -r "' + CFG.localDist + '\\*" ' + CFG.sshUser + '@' + CFG.sshHost + ':"' + CFG.remoteDist + '/"';
  console.log('[SCP]', cmd);
  execSync(cmd, { stdio: 'inherit' });
  console.log('    OK');

  console.log('[3/4] fix perms');
  await sh('chown -R nwparty:nwparty ' + CFG.remoteDist + ' 2>/dev/null || true; echo PERM_OK');
  console.log('    OK');

  console.log('[4/4] verify');
  const r = await sh('curl -sI http://127.0.0.1:8081/ | head -3');
  console.log(r.stdout);
  if (!r.stdout.includes('200')) throw new Error('nginx did not return 200');

  console.log();
  console.log('============================================================');
  console.log('  frontend publish OK');
  console.log('  backup: ' + REMOTE_BACKUP);
  console.log('  rollback: node rollback.cjs ' + TIMESTAMP);
  console.log('============================================================');
})().catch(e => {
  console.error('FAIL:', e.message);
  process.exit(1);
});
