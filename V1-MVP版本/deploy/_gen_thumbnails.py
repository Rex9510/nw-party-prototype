"""为现有 activity_attachments 一次性生成缩略图

- 读 kind='photo' 的 file_url（base64 dataURL）
- 用 PIL 压缩到 200x200，JPEG 质量 60
- 写回 thumbnail_url 字段

非 photo（word/excel/pdf）跳过。
"""
import sys, os, asyncio, base64, io
sys.path.insert(0, '/var/www/nwparty/src/backend')

# 从 .env 读 DATABASE_URL（否则 settings 走 PG 默认连接）
from dotenv import dotenv_values
env = dotenv_values('/var/www/nwparty/.env')
os.environ.update({k: v for k, v in env.items() if v is not None})

from PIL import Image
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.activity import ActivityAttachment


def make_thumb(data_url: str) -> str | None:
    """data:image/jpeg;base64,... → 200x200 JPEG base64 dataURL。"""
    if not data_url:
        return None
    if not data_url.startswith('data:image/'):
        return None
    try:
        head, b64 = data_url.split(',', 1)
        mime = head.split(';', 1)[0].split(':', 1)[1]
        raw = base64.b64decode(b64)
        img = Image.open(io.BytesIO(raw))
        img = img.convert('RGB')
        img.thumbnail((200, 200), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=60)
        b64_small = base64.b64encode(buf.getvalue()).decode('ascii')
        return f'data:{mime};base64,{b64_small}'
    except Exception as e:
        print(f'  FAIL: {e}')
        return None


async def main():
    async with AsyncSessionLocal() as s:
        r = await s.execute(select(ActivityAttachment).where(ActivityAttachment.kind == 'photo'))
        atts = r.scalars().all()
        print(f'Found {len(atts)} photo attachments')
        for att in atts:
            if att.thumbnail_url:
                print(f'  skip {att.id} (already has thumbnail)')
                continue
            print(f'  processing {att.id} activity={att.activity_id} orig_size={len(att.file_url or "")}')
            thumb = make_thumb(att.file_url)
            if thumb:
                att.thumbnail_url = thumb
                s.add(att)
                print(f'    OK thumb_size={len(thumb)}')
        await s.commit()
        print('DONE')


if __name__ == '__main__':
    asyncio.run(main())
