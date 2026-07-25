"""/api/v1/study-hours 测试。"""
import pytest
from httpx import AsyncClient


async def _login(c, phone, pwd):
    r = await c.post("/api/v1/auth/login", json={"phone": phone, "password": pwd})
    return r.json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


async def _create_approved_activity(client, admin_token, sample_data, member_phone, study_hours=4.0):
    """完整流程：录入 → 加照片 → 提交 → 社区初审 → 街道复审"""
    headers = _auth(admin_token)
    # 创建党员
    r = await client.post(
        "/api/v1/members",
        json={"name": "测试党员", "phone": member_phone, "branch_id": sample_data["branch_id"]},
        headers=headers,
    )
    mid = r.json()["id"]
    # 录入活动
    r = await client.post(
        "/api/v1/activities",
        json={
            "organizer_branch_id": sample_data["branch_id"],
            "training_at": "2026-04-09T10:00:00",
            "location": "会议室",
            "theme": "测试培训",
            "participant_count": 1,
            "online_offline": "offline",
            "is_centralized": True,
            "is_innovation_theory": True,
            "source_type": "self_organize",
            "audience_category": "community_member",
            "study_hours": study_hours,
            "participants": [{"member_id": mid, "study_hours": study_hours, "attendance_status": "signed"}],
            "photo_count": 1,
        },
        headers=headers,
    )
    aid = r.json()["id"]
    await client.post(
        f"/api/v1/activities/{aid}/attachments",
        json={"kind": "photo", "file_url": "https://example.com/p.jpg"},
        headers=headers,
    )
    # 提交
    await client.post(f"/api/v1/activities/{aid}/submit", headers=headers)
    # 社区初审
    org_token = await _login(client, "13800000002", "org123")
    await client.post(f"/api/v1/audits/{aid}/approve", json={"comment": "ok"}, headers=_auth(org_token))
    # 街道复审
    lead_token = await _login(client, "13800000001", "lead123")
    await client.post(f"/api/v1/audits/{aid}/approve", json={"comment": "ok"}, headers=_auth(lead_token))
    return aid, mid


class TestStudyHours:
    @pytest.mark.asyncio
    async def test_me_no_member_returns_empty(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        r = await client.get("/api/v1/study-hours/me?year=2026", headers=_auth(admin_token))
        assert r.status_code == 200
        # admin 没有 member 记录，返回空
        assert float(r.json()["total_hours"]) == 0
        assert r.json()["activity_count"] == 0

    @pytest.mark.asyncio
    async def test_member_self_view_after_approved(self, client, sample_data):
        # 创建一个 approved 活动
        admin_token = await _login(client, "13800000000", "admin123")
        await _create_approved_activity(client, admin_token, sample_data, "13800001111", 4.0)

        # 用 member 手机号登录 —— 需要先有这个 user 账号。简化：admin 查 detail
        r = await client.get("/api/v1/study-hours/1?year=2026", headers=_auth(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["year"] == 2026
        assert float(data["total_hours"]) == 4.0
        assert data["activity_count"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_yearly_list(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        await _create_approved_activity(client, admin_token, sample_data, "13800001111", 4.0)

        r = await client.get("/api/v1/study-hours?year=2026", headers=_auth(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["year"] == 2026
        assert data["total_members"] == 1
        assert float(data["items"][0]["total_hours"]) == 4.0

    @pytest.mark.asyncio
    async def test_list_respects_role_scope(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        await _create_approved_activity(client, admin_token, sample_data, "13800001111", 4.0)

        # 街道负责人：全街道
        lead_token = await _login(client, "13800000001", "lead123")
        r = await client.get("/api/v1/study-hours?year=2026", headers=_auth(lead_token))
        assert r.json()["total_members"] == 1

        # 社区委员：本社区
        org_token = await _login(client, "13800000002", "org123")
        r = await client.get("/api/v1/study-hours?year=2026", headers=_auth(org_token))
        assert r.json()["total_members"] == 1

    @pytest.mark.asyncio
    async def test_multiple_activities_accumulate(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        # 两场活动，3 + 5 = 8 学时
        await _create_approved_activity(client, admin_token, sample_data, "13800001111", 3.0)
        await _create_approved_activity(client, admin_token, sample_data, "13800001112", 5.0)

        r = await client.get("/api/v1/study-hours/1?year=2026", headers=_auth(admin_token))
        data = r.json()
        # 第一个 member 只有 1 场活动
        assert data["activity_count"] == 1
        assert float(data["total_hours"]) == 3.0

        r = await client.get("/api/v1/study-hours/2?year=2026", headers=_auth(admin_token))
        data = r.json()
        assert data["activity_count"] == 1
        assert float(data["total_hours"]) == 5.0
