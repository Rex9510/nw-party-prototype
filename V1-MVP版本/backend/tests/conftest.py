"""
Pytest fixtures：异步 SQLAlchemy + aiosqlite 内存库。
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app as fastapi_app
import app.db.base  # noqa: F401
from app.models.dict import TrainingCategory, TrainingSource
from app.models.party import Branch, Community, Street
from app.models.user import User


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False, "uri": True},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _fk_off(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=OFF")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def sample_data(session_factory):
    async with session_factory() as s:
        street = Street(name="南湾街道")
        s.add(street)
        await s.flush()

        community = Community(street_id=street.id, name="南湾社区")
        s.add(community)
        await s.flush()

        branch = Branch(community_id=community.id, name="南湾社区第一党支部")
        s.add(branch)
        await s.flush()

        admin = User(
            phone="13800000000",
            password_hash=hash_password("admin123"),
            name="系统管理员",
            role=User.ROLE_ADMIN,
            street_id=street.id,
            status="active",
        )
        street_lead = User(
            phone="13800000001",
            password_hash=hash_password("lead123"),
            name="张主任",
            role=User.ROLE_STREET_LEAD,
            street_id=street.id,
            status="active",
        )
        community_org = User(
            phone="13800000002",
            password_hash=hash_password("org123"),
            name="李委员",
            role=User.ROLE_COMMUNITY_ORG,
            street_id=street.id,
            community_id=community.id,
            status="active",
        )
        s.add_all([admin, street_lead, community_org])
        await s.commit()

        # 字典种子（与 scripts/seed.py 一致）
        for code, name, sort in [
            ("community_member", "社区党员", 1),
            ("govt_member", "机关党员", 2),
            ("ngo_member", "两新党组织党员", 3),
        ]:
            if not (await s.execute(
                select(TrainingCategory).where(TrainingCategory.code == code)
            )).scalar_one_or_none():
                s.add(TrainingCategory(code=code, name=name, sort=sort))
        for code, name, sort in [
            ("upper_send", "上级送课", 1),
            ("self_organize", "自行组织", 2),
        ]:
            if not (await s.execute(
                select(TrainingSource).where(TrainingSource.code == code)
            )).scalar_one_or_none():
                s.add(TrainingSource(code=code, name=name, sort=sort))
        await s.commit()

    return {
        "street_id": street.id,
        "community_id": community.id,
        "branch_id": branch.id,
        "admin_phone": admin.phone,
        "lead_phone": street_lead.phone,
        "org_phone": community_org.phone,
    }


@pytest_asyncio.fixture
async def client(session_factory, sample_data):
    async def _override_get_db():
        async with session_factory() as s:
            yield s

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    fastapi_app.dependency_overrides.clear()
