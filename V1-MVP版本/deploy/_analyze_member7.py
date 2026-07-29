"""分析 member_id=7 的响应体为何 5.8MB"""
import sys, os, json, sqlite3
sys.path.insert(0, '/var/www/nwparty/src/backend')
os.environ['JWT_SECRET'] = 'bJU0IISYL2PsI3w6qhH9vvHqDTF-iSdvmPvFi1jYfs1YZIQffj2j90waORLMscPt'

# 1) 看 photo_urls 长度
con = sqlite3.connect('/var/www/nwparty/data/nwparty.db')
cur = con.execute("select length(photo_urls) from members where id=7")
plen = cur.fetchone()[0]
print(f'member 7 photo_urls length: {plen} bytes')

# 2) 看他的活动参与 + 附件大小
cur = con.execute("""
    select a.id, a.theme, a.status,
        (select count(*) from activity_attachments where activity_id=a.id) cnt,
        (select coalesce(sum(length(file_url)),0) from activity_attachments where activity_id=a.id and kind='photo') photo_bytes,
        (select coalesce(sum(length(file_url)),0) from activity_attachments where activity_id=a.id and kind!='photo') att_bytes
    from activities a
    join activity_participants p on p.activity_id=a.id
    where p.member_id=7
    order by a.id
""")
total_photo = 0
total_att = 0
for row in cur.fetchall():
    a_id, theme, status, cnt, photo_bytes, att_bytes = row
    print(f'  activity {a_id} "{theme[:30]}" status={status} atts={cnt} photo={photo_bytes}B att={att_bytes}B')
    total_photo += photo_bytes
    total_att += att_bytes
con.close()
print(f'\n总 photo 字段字节: {total_photo}')
print(f'总 attachment 字段字节: {total_att}')
print(f'member photo_urls 字段: {plen}')
print(f'估算响应体: {plen + total_photo + total_att} bytes')
