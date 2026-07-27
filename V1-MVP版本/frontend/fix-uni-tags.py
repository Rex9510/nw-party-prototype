"""
批量把 uni-app 标签转 web：
- <view → <div
- </view> → </div>
- <text → <span
- </text> → </span>
- <image → <img
- </image> → </img>
- <scroll-view → <div class="scroll"
- </scroll-view> → </div>
- <picker → <div class="picker" （保留 @change 用 v-on:change）
- </picker> → </div>
- <input> 已和 web 一样
- <button> 已和 web 一样
- 单位：rpx → px（除以2，rpx 750 = 375px）
"""
import re
import sys
from pathlib import Path

PAGES = Path(r'D:\项目\党组织项目\V1-MVP版本\frontend\src\pages')

replacements = [
    (r'<view\b', '<div'),
    (r'</view>', '</div>'),
    (r'<text\b', '<span'),
    (r'</text>', '</span>'),
    (r'<image\b', '<img'),
    (r'</image>', '</img>'),
    (r'<scroll-view\b', '<div class="scroll"'),
    (r'</scroll-view>', '</div>'),
    (r'<picker\b', '<div class="picker"'),
    (r'</picker>', '</div>'),
    # rpx 数值转 px（除以2，简化处理）
    (r'(\d+)rpx', lambda m: f'{int(int(m.group(1)) / 2)}px'),
]

for f in PAGES.rglob('*.vue'):
    text = f.read_text(encoding='utf-8')
    new_text = text
    for pat, rep in replacements:
        if callable(rep):
            new_text = re.sub(pat, rep, new_text)
        else:
            new_text = re.sub(pat, rep, new_text)
    if new_text != text:
        f.write_text(new_text, encoding='utf-8')
        print(f'fixed: {f.name}')
print('done')
