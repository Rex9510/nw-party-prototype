# -*- coding: utf-8 -*-
import re
path = r'E:\new party\nw-party-prototype\V1-MVP版本\backend\app\api\v1\activities.py'
with open(path, 'rb') as f:
    data = f.read()
# 找 0x3f 紧接中文字符的位置（损坏特征）
lines = data.split(b'\n')
issues = 0
for i, line in enumerate(lines, 1):
    # 中文字符 3 字节 UTF-8，? 0x3f 不在中文里
    # 模式: 中文(3 字节) + 0x3f + 中文(3 字节) 或 中文(3 字节) + 0x3f + 0x22
    for m in re.finditer(rb'[\xe4-\xe9][\x80-\xbf][\x80-\xbf]\?[\xe4-\xe9\x22]', line):
        issues += 1
        if issues <= 20:
            ctx = line[max(0, m.start()-15):m.end()+15]
            print(f'line {i} (offset {m.start()}): {ctx!r}')
print(f'total {issues} issues')
