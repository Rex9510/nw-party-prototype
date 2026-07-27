// ============================================================================
// 党员学时统计系统 V1-MVP · PM2 配置
// ----------------------------------------------------------------------------
// 调 start-backend.sh（它会 source .env 再 exec gunicorn）
// 不用 fork 多 instances，gunicorn 自己管 worker
// ============================================================================
module.exports = {
  apps: [
    {
      name: 'nwparty-api',
      script: '/var/www/nwparty/config/start-backend.sh',
      // 关键：interpreter 让 PM2 知道用 bash 跑
      interpreter: 'bash',
      interpreter_args: '-c',
      exec_mode: 'fork',
      instances: 1,
      autorestart: true,
      max_restarts: 5,
      min_uptime: '10s',
      kill_timeout: 8000,
      wait_ready: false,
      // 日志
      out_file: '/var/log/nwparty/pm2-out.log',
      error_file: '/var/log/nwparty/pm2-error.log',
      merge_logs: true,
    },
  ],
};
