"""为现有 photo attachments 生成缩略图（不依赖 ORM commit，直接 SQL 写入）

绕过 SQLAlchemy ORM commit 时的反射问题（activity_attachments FK 引用了不存在的 activities_old）。
"""
import sys, os, base64, io, sqlite3
sys.path.insert(0, '/var/www/nwparty/src/backend')

from PIL import Image

DB_PATH = '/var/www/nwparty/data/nwparty.db'

def make_thumb(data_url: str) -> str | None:
    if not data_url or not data_url.startswith('data:image/'):
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
        return f'data:{mime};base64,{base64.b64encode(buf.getvalue()).decode("ascii")}'
    except Exception as e:
        print(f'  FAIL: {e}')
        return None


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.execute("select id, file_url, thumbnail_url from activity_attachments where kind='photo'")
    rows = cur.fetchall()
    print(f'Found {len(rows)} photo attachments')
    for att_id, file_url, thumb_old in rows:
        if thumb_old:
            print(f'  skip {att_id} (already has thumbnail)')
            continue
        print(f'  processing {att_id} orig_size={len(file_url or "")}')
        thumb = make_thumb(file_url)
        if thumb:
            con.execute("update activity_attachments set thumbnail_url=? where id=?", (thumb, att_id))
            print(f'    OK thumb_size={len(thumb)}')
    con.commit()
    con.close()
    print('DONE')


if __name__ == '__main__':
    main()
