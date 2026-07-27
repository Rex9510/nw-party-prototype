"""直接调函数验证。"""
import sys
sys.path.insert(0, '/var/www/nwparty/src/backend')
import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.member import Member
from app.models.user import User

async def go():
    async with AsyncSessionLocal() as s:
        r = await s.execute(
            select(Member).where(Member.branch_id == 1, Member.status == 'dimission')
        )
        m = r.scalars().all()
        print('dimission members in branch 1:', [(x.id, x.name, x.status, x.branch_id) for x in m])

        r2 = await s.execute(select(User).where(User.branch_id == 1))
        u = r2.scalars().all()
        print('users in branch 1:', [(x.id, x.phone, x.name, x.branch_id) for x in u])

asyncio.run(go())
