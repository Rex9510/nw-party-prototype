// publish-backend.cjs
// Push backend code + run alembic migration + pm2 restart
// Usage: node publish-backend.cjs
// Config: SSH_KEY_PATH env var, default C:\Users\rex.zhu\.ssh\rex_root.pem
const { Client } = require('ssh2');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const CFG = {
  sshKey: process.env.SSH_KEY_PATH || 'C:\\Users\\rex.zhu\\.ssh\\rex_root.pem',
  sshUser: 'root',
  sshHost: '47.107.77.15',
  remoteHome: '/var/www/nwparty',
  remoteSrc: '/var/www/nwparty/src/backend',
  remoteVenv: '/var/www/nwparty/venv',
  backupRoot: '/var/backups/nwparty/code',
  localBackend: path.resolve(__dirname, '..', 'backend'),
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

function scpDir(localDir, remoteDir) {
  const cmd = 'scp -i "' + CFG.sshKey + '" -o StrictHostKeyChecking=no -r "' + localDir + '\\*" ' + CFG.sshUser + '@' + CFG.sshHost + ':"' + remoteDir + '/"';
  console.log('[SCP]', cmd);
  execSync(cmd, { stdio: 'inherit' });
}

(async () => {
  console.log('============================================================');
  console.log('  nwparty backend publish');
  console.log('============================================================');
  console.log('local:  ' + CFG.localBackend);
  console.log('remote: ' + CFG.remoteSrc);
  console.log('backup: ' + REMOTE_BACKUP);
  console.log();

  if (!fs.existsSync(CFG.localBackend)) throw new Error('local backend missing: ' + CFG.localBackend);
  if (!fs.existsSync(path.join(CFG.localBackend, 'app'))) throw new Error('local backend missing app/');
  if (!fs.existsSync(CFG.sshKey)) throw new Error('SSH key missing: ' + CFG.sshKey);

  console.log('[1/5] backup current remote code');
  await sh('mkdir -p ' + CFG.backupRoot + ' && if [ -d ' + CFG.remoteSrc + ' ]; then cp -r ' + CFG.remoteSrc + ' ' + REMOTE_BACKUP + '; else mkdir -p ' + REMOTE_BACKUP + '; fi && echo BACKUP_OK');
  console.log('    OK');

  console.log('[2/5] upload new backend');
  await sh('rm -rf ' + CFG.remoteSrc + ' && mkdir -p ' + CFG.remoteSrc);
  scpDir(CFG.localBackend, CFG.remoteSrc);
  console.log('    OK');

  console.log('[3/5] fix perms + reinstall deps');
  const setupCmd = 'set -e\n'
    + 'cd ' + CFG.remoteSrc + '\n'
    + 'chmod +x ' + CFG.remoteVenv + '/bin/* 2>/dev/null || true\n'
    + 'source ' + CFG.remoteVenv + '/bin/activate\n'
    + 'pip install -q -r requirements.txt\n'
    + 'chown -R nwparty:nwparty ' + CFG.remoteSrc + '\n'
    + 'echo SETUP_OK';
  await sh(setupCmd);
  console.log('    OK');

  console.log('[4/5] alembic upgrade head');
  // 必须从 /var/www/nwparty/.env 读 DATABASE_URL，否则 alembic env.py 走 settings.database_url 默认 PG（连不上）
  // 2026_07_27 教训：第一次发布后 alembic_version 留在了 2026_07_25_0001（sort 列实际有但 alembic 不知道）。
  // 第二次发布：current=2026_07_25_0001，head=2026_07_27_0002；upgrade 会从 0001 跑到 head，中
  //   间会重跑 0001（add sort）→ 失败。先 stamp 到 0001（sort 已存在），再 upgrade 跑 0002。
  const migrateCmd = 'set -e\n'
    + 'source ' + CFG.remoteVenv + '/bin/activate\n'
    + 'cd ' + CFG.remoteSrc + '\n'
    + 'export $(cat ' + CFG.remoteHome + '/.env | grep -v "^#" | xargs)\n'
    + 'echo "DATABASE_URL=$DATABASE_URL"\n'
    + 'echo "current:"\n'
    + 'alembic current || true\n'
    + 'echo "head:"\n'
    + 'alembic heads || true\n'
    + 'echo "smoke check DB state:"\n'
    + 'sqlite3 /var/www/nwparty/data/nwparty.db "SELECT version_num FROM alembic_version; SELECT name FROM pragma_table_info(\'streets\') WHERE name=\'sort\';" || true\n'
    + 'CURR=$(sqlite3 /var/www/nwparty/data/nwparty.db "SELECT version_num FROM alembic_version" 2>/dev/null || echo "")\n'
    + 'HASSORT=$(sqlite3 /var/www/nwparty/data/nwparty.db "SELECT count(*) FROM pragma_table_info(\'streets\') WHERE name=\'sort\'" 2>/dev/null || echo "0")\n'
    + 'echo "current=$CURR streets_has_sort=$HASSORT"\n'
    + 'if [ "$CURR" = "2026_07_25_0001" ] && [ "$HASSORT" = "1" ]; then echo "STAMPING forward to 2026_07_27_0001"; alembic stamp 2026_07_27_0001; fi\n'
    + 'alembic upgrade head\n'
    + 'echo MIGRATE_OK';
  try {
    await sh(migrateCmd);
    console.log('    OK');
  } catch (e) {
    console.error('!!! alembic migration failed', e.message);
    throw new Error('migration failed, please run: node rollback-backend.cjs ' + TIMESTAMP);
  }

  console.log('[5/5] fix log perms + pm2 reload + kill orphan gunicorn + health check');
  // 关键：pm2 restart 不够！gunicorn master 不会重新 spawn worker 加载新代码。
  // 必须 pm2 delete + start，让 gunicorn 完全重新加载（实测教训：v1 改了 10 个新接口全部 404，pm2 restart 没生效）
  // + 必须先 chown 日志（root:root 会让新 gunicorn PermissionError 启动失败，PM2 循环 crash，老 gunicorn 不被 kill 继续服务旧代码）
  // + 必须 pkill gunicorn 兜底：万一 PM2 没接管所有 gunicorn 进程（fork 模式），老进程会一直跑
  const restartCmd = 'set -e\n'
    + 'chown nwparty:nwparty /var/log/nwparty/access.log /var/log/nwparty/error.log 2>/dev/null || true\n'
    + 'sudo -u nwparty PM2_HOME=' + CFG.remoteHome + '/.pm2 pm2 delete nwparty-api 2>/dev/null || true\n'
    + 'sleep 2\n'
    + 'pkill -f "gunicorn.*app.main" 2>/dev/null || true\n'
    + 'sleep 2\n'
    + 'sudo -u nwparty PM2_HOME=' + CFG.remoteHome + '/.pm2 pm2 start ' + CFG.remoteHome + '/ecosystem.config.cjs\n'
    + 'sleep 5\n'
    + 'curl -s http://127.0.0.1:8000/health\n'
    + 'echo "openapi move paths:"\n'
    + 'curl -s http://127.0.0.1:8000/openapi.json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(p) for p in sorted(d.get(\'paths\',{}).keys()) if \'move\' in p]"';
  const r = await sh(restartCmd);
  console.log(r.stdout);
  if (!r.stdout.includes('"status":"ok"')) {
    throw new Error('/health did not return ok, please rollback immediately');
  }

  console.log();
  console.log('============================================================');
  console.log('  backend publish OK');
  console.log('  backup: ' + REMOTE_BACKUP);
  console.log('  rollback: node rollback-backend.cjs ' + TIMESTAMP);
  console.log('============================================================');
})().catch(e => {
  console.error('FAIL:', e.message);
  process.exit(1);
});
