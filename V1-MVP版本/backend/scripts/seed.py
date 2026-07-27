"""
种子数据脚本：街道/社区/支部/字典/全部角色测试账号。

用法：
    python -m scripts.seed
或：
    docker compose exec api python -m scripts.seed

幂等：重复运行不会重复插入。
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
        # 1. 街道（示例 3 个）
        streets_data = ['南湾街道', '桃源街道', '科技园街道']
        streets = []
        for name in streets_data:
            r = await db.execute(select(Street).where(Street.name == name))
            s = r.scalar_one_or_none()
            if not s:
                s = Street(name=name)
                db.add(s)
                await db.flush()
                print(f'* 创建街道: {s.name} (id={s.id})')
            streets.append(s)

        # 2. 社区（每个街道 2 个示例社区）
        community_map: dict[int, list[str]] = {
            streets[0].id: ['南岭社区', '中心社区'],
            streets[1].id: ['桃源社区', '龙湖社区'],
            streets[2].id: ['科技园社区', '高新社区'],
        }
        all_communities = []
        for street_id, names in community_map.items():
            for name in names:
                r = await db.execute(
                    select(Community).where(Community.street_id == street_id, Community.name == name)
                )
                c = r.scalar_one_or_none()
                if not c:
                    c = Community(street_id=street_id, name=name)
                    db.add(c)
                    await db.flush()
                    print(f'* 创建社区: {c.name} (id={c.id})')
                all_communities.append(c)

        # 3. 支部（每个社区 2 个示例支部）
        for c in all_communities:
            for suffix in ['第一党支部', '第二党支部']:
                name = f'{c.name}{suffix}'
                r = await db.execute(
                    select(Branch).where(Branch.community_id == c.id, Branch.name == name)
                )
                b = r.scalar_one_or_none()
                if not b:
                    b = Branch(community_id=c.id, name=name)
                    db.add(b)
                    await db.flush()
                    print(f'* 创建支部: {b.name} (id={b.id})')

        # 4. 字典：培训对象类别
        categories = [
            ('community_member', '社区党员', 1),
            ('govt_member', '机关党员', 2),
            ('ngo_member', '两新党组织党员', 3),
            ('other', '其他', 4),
        ]
        for code, name, sort in categories:
            r = await db.execute(select(TrainingCategory).where(TrainingCategory.code == code))
            if not r.scalar_one_or_none():
                db.add(TrainingCategory(code=code, name=name, sort=sort))
                print(f'* 培训类别: {name}')

        # 5. 字典：培训来源
        sources = [('upper_send', '上级送课', 1), ('self_organize', '自行组织', 2)]
        for code, name, sort in sources:
            r = await db.execute(select(TrainingSource).where(TrainingSource.code == code))
            if not r.scalar_one_or_none():
                db.add(TrainingSource(code=code, name=name, sort=sort))
                print(f'* 培训来源: {name}')

        # 6. 字典：讲师
        r = await db.execute(select(Lecturer).where(Lecturer.name == '王教授'))
        if not r.scalar_one_or_none():
            db.add(Lecturer(name='王教授', intro='市委党校教授，长期从事党建理论研究'))
            print('* 讲师: 王教授')
        r = await db.execute(select(Lecturer).where(Lecturer.name == '李老师'))
        if not r.scalar_one_or_none():
            db.add(Lecturer(name='李老师', intro='街道党校讲师，擅长基层党员教育'))
            print('* 讲师: 李老师')

        # 7. 测试账号（5 个角色各 1 个，全部用密码 pass1234）
        # 用第 1 个街道、社区、支部做默认归属
        default_street_id = streets[0].id
        default_community_id = all_communities[0].id
        # 第 1 个社区下的第 1 个支部
        first_branch_id = None
        r = await db.execute(
            select(Branch).where(Branch.community_id == default_community_id).order_by(Branch.id)
        )
        b = r.scalars().first()
        if b:
            first_branch_id = b.id

        accounts = [
            ('13800000000', 'pass1234', '系统管理员', User.ROLE_ADMIN,
             default_street_id, None, None),
            ('13800000001', 'pass1234', '张主任（街道）', User.ROLE_STREET_LEAD,
             default_street_id, None, None),
            ('13800000002', 'pass1234', '李委员（社区）', User.ROLE_COMMUNITY_ORG,
             default_street_id, default_community_id, None),
            ('13800000003', 'pass1234', '陈书记（支部）', User.ROLE_BRANCH_SEC,
             default_street_id, default_community_id, first_branch_id),
            ('13800000010', 'pass1234', '张三（党员）', User.ROLE_MEMBER,
             default_street_id, default_community_id, first_branch_id),
        ]
        for phone, pwd, name, role, sid, cid, bid in accounts:
            r = await db.execute(select(User).where(User.phone == phone))
            user = r.scalar_one_or_none()
            if not user:
                db.add(User(
                    phone=phone,
                    password_hash=hash_password(pwd),
                    name=name,
                    role=role,
                    street_id=sid,
                    community_id=cid,
                    branch_id=bid,
                    status='active',
                ))
                print(f'* 新建账号: {phone} / {pwd}  →  {name} ({role})')
            else:
                # 已存在则强制同步密码和所属组织（本地 dev 库，方便测试）
                user.password_hash = hash_password(pwd)
                user.name = name
                user.role = role
                user.street_id = sid
                user.community_id = cid
                user.branch_id = bid
                user.status = 'active'
                print(f'~ 同步账号: {phone} / {pwd}  →  {name} ({role})')

        await db.commit()
        print('\n种子数据完成')
        print()
        print('=' * 60)
        print('  测试账号（密码全部为 pass1234）:')
        print('  13800000000  系统管理员')
        print('  13800000001  街道负责人')
        print('  13800000002  社区组织委员')
        print('  13800000003  支部书记')
        print('  13800000010  党员（张三）')
        print('=' * 60)


if __name__ == '__main__':
    asyncio.run(seed())
