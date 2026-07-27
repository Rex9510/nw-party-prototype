"""临时调试用：检查 schema 是否认识新字段。"""
import sys
sys.path.insert(0, '/var/www/nwparty/src/backend')
from app.schemas.member import MemberBase, MemberCreate

# 默认值
b = MemberBase(name='x', phone='13800000001')
print('default is_mobile_member:', b.is_mobile_member)
print('default flow_in_date:', b.flow_in_date)
print('---')

# is_mobile=True 不带 flow_in_date -> 应报错
try:
    b2 = MemberBase(name='x', phone='13800000001', is_mobile_member=True)
    print('UNEXPECTED OK:', b2.model_dump())
except Exception as e:
    print('EXPECTED ERR:', type(e).__name__, e)

print('---')

# is_mobile=True + flow_in_date -> OK
b3 = MemberBase(name='x', phone='13800000001', is_mobile_member=True, flow_in_date='2024-01-01')
print('OK:', b3.model_dump())

print('---')

# 测试从 ORM 读
from app.models.member import Member
from app.schemas.member import MemberOut
import asyncio
from app.db.session import async_session

async def go():
    async with async_session() as s:
        from sqlalchemy import select
        r = await s.execute(select(Member).limit(1))
        m = r.scalar_one()
        print('ORM attrs:', m.is_mobile_member, m.flow_in_date)
        mo = MemberOut.model_validate(m)
        print('MemberOut dump:', mo.model_dump())

asyncio.run(go())
