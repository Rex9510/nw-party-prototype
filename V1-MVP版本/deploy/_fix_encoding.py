# -*- coding: utf-8 -*-
path = r'E:\new party\nw-party-prototype\V1-MVP版本\backend\app\api\v1\activities.py'
with open(path, 'rb') as f:
    data = f.read()

# 先定位损坏的 docstring: 4 空格 + """ + 一串乱码 + 0x3f + """ + 0d
# 乱码字节: e5 a8 b2 e8 af b2 e5 a7 a9 e9 8d 92 e6 a5 84 e3 80 83 e9 8a 86
# 正确 "活动列表。": e6 b4 bb e5 8a a8 e5 88 97 e8 a1 a8 e3 80 82
old = b'"""' + b'\xe5\xa8\xb2\xe8\xaf\xb2\xe5\xa7\xa9\xe9\x8d\x92\xe6\xa5\x84\xe3\x80\x83\xe9\x8a\x86' + b'?' + b'"""'
new = b'"""' + '活动列表。'.encode('utf-8') + b'"""'
print('old in data:', old in data)
print('old bytes:', old)
print('new bytes:', new)
if old in data:
    data = data.replace(old, new)
    print('replaced, new size:', len(data))
    with open(path, 'wb') as f:
        f.write(data)
    print('saved')
else:
    print('not found, leaving file as-is')
