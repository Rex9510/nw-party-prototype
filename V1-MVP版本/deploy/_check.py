import sys
for _s in ('stdout','stderr'):
    getattr(sys,_s).reconfigure(encoding='utf-8', errors='replace')
with open(r'E:\new party\nw-party-prototype\V1-MVP版本\backend\app\api\v1\activities.py.bak', 'r', encoding='utf-8') as f:
    src = f.read()
old = '    # 校验支部存在 + 权限'
print('count old_simple:', src.count(old))
# show actual lines
lines = src.split('\n')
for i, l in enumerate(lines, 1):
    if '校验支部存在' in l:
        print(f'line {i}: {l!r}')
        for j in range(i, min(i+22, len(lines))):
            print(f'  +{j-i}: {lines[j]!r}')
        break
