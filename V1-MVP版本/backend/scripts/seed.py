"""
种子数据脚本：街道/社区/支部/字典/初始超管账号。

用法：
    python -m scripts.seed
或：
    docker compose exec api python -m scripts.seed
"""
import asyncio
import sys
from pathlib import Path

# 让脚本能找到 app/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.dict import Lecturer, TrainingCategory, TrainingSource
from app.models.party import Branch, Community, Street
from app.models.user import User


async def seed():
    async with AsyncSessionLocal() as db:
        # 1. 街道
        result = await db.execute(select(Street).where(Street.name == '南湾街道'))
        street = result.scalar_one_or_none()
        if not street:
            street = Street(name='南湾街道')
            db.add(street)
            await db.flush()
            print(f'✓ 创建街道: {street.name} (id={street.id})')
        else:
            print(f'- 街道已存在: {street.name}')

        # 2. 字典：培训对象类别
        categories = [
            ('community_member', '社区党员', 1),
            ('govt_member', '机关党员', 2),
            ('ngo_member', '两新党组织党员', 3),
        ]
        for code, name, sort in categories:
            r = await db.execute(select(TrainingCategory).where(TrainingCategory.code == code))
            if not r.scalar_one_or_none():
                db.add(TrainingCategory(code=code, name=name, sort=sort))
                print(f'✓ 培训类别: {name}')

        # 3. 字典：培训来源
        sources = [('upper_send', '上级送课', 1), ('self_organize', '自行组织', 2)]
        for code, name, sort in sources:
            r = await db.execute(select(TrainingSource).where(TrainingSource.code == code))
            if not r.scalar_one_or_none():
                db.add(TrainingSource(code=code, name=name, sort=sort))
                print(f'✓ 培训来源: {name}')

        # 4. 初始超管账号
        r = await db.execute(select(User).where(User.phone == '13800000000'))
        if not r.scalar_one_or_none():
            admin = User(
                phone='13800000000',
                password_hash=hash_password('admin123'),
                name='系统管理员',
                role=User.ROLE_ADMIN,
                street_id=street.id,
                status='active',
            )
            db.add(admin)
            print(f'✓ 初始超管: phone=13800000000 / password=admin123')
        else:
            print('- 超管账号已存在')

        await db.commit()
        print('\n种子数据完成')


if __name__ == '__main__':
    asyncio.run(seed())
