"""检查远程服务器的 __pycache__ 情况，输出重定向到文件避免编码问题"""
import subprocess, sys

SSH_KEY = r'C:\Users\rex.zhu\.ssh\rex_root.pem'
SSH_HOST = 'root@47.107.77.15'

# 先把检查脚本传到服务器
scp_cmd = ['scp', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
           r'E:\new party\nw-party-prototype\V1-MVP版本\deploy\_check_pycache_remote.sh',
           f'{SSH_HOST}:/tmp/_check_pycache.sh']
subprocess.run(scp_cmd, timeout=15)

# 然后在服务器上执行
cmd = ['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no', SSH_HOST, 'bash /tmp/_check_pycache.sh']
r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, errors='replace')
print('STDOUT:')
print(r.stdout)
print('---STDERR---')
print(r.stderr[:1000])
print(f'EXIT: {r.returncode}')
