"""/api/v1/stats 测试。"""
import pytest
from httpx import AsyncClient


async def _login(c, phone, pwd):
    r = await c.post("/api/v1/auth/login", json={"phone": phone, "password": pwd})
    return r.json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


async def _create_approved_activity(
    client, admin_token, sample_data, *,
    source_type="self_organize",
    audience_category="community_member",
    participant_count=10,
    study_hours=4.0,
    member_phone="13800001111",
):
    """完整流程：录入 → 提交 → 社区初审 → 街道复审"""
    headers = _auth(admin_token)
    r = await client.post(
        "/api/v1/members",
        json={"name": "测试党员", "phone": member_phone, "branch_id": sample_data["branch_id"]},
        headers=headers,
    )
    mid = r.json()["id"]
    r = await client.post(
        "/api/v1/activities",
        json={
            "organizer_branch_id": sample_data["branch_id"],
            "training_at": "2026-04-09T10:00:00",
            "location": "会议室",
            "theme": "测试",
            "participant_count": participant_count,
            "online_offline": "offline",
            "is_centralized": True,
            "is_innovation_theory": True,
            "source_type": source_type,
            "audience_category": audience_category,
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
    await client.post(f"/api/v1/activities/{aid}/submit", headers=headers)
    org_token = await _login(client, "13800000002", "org123")
    await client.post(f"/api/v1/audits/{aid}/approve", json={"comment": "ok"}, headers=_auth(org_token))
    lead_token = await _login(client, "13800000001", "lead123")
    await client.post(f"/api/v1/audits/{aid}/approve", json={"comment": "ok"}, headers=_auth(lead_token))
    return aid


class TestYearlyStats:
    @pytest.mark.asyncio
    async def test_empty_year(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        r = await client.get("/api/v1/stats/yearly?year=2026", headers=_auth(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["year"] == 2026
        assert len(data["items"]) == 6
        assert data["total_sessions"] == 0

    @pytest.mark.asyncio
    async def test_approved_activities_counted(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        # 2 场 "送课到社区"（upper_send + community）
        await _create_approved_activity(
            client, admin_token, sample_data,
            source_type="upper_send", audience_category="community_member",
            participant_count=20, member_phone="13800001111",
        )
        await _create_approved_activity(
            client, admin_token, sample_data,
            source_type="upper_send", audience_category="community_member",
            participant_count=30, member_phone="13800002222",
        )
        # 1 场 "党建组"（self_organize + govt）
        await _create_approved_activity(
            client, admin_token, sample_data,
            source_type="self_organize", audience_category="govt_member",
            participant_count=15, member_phone="13800003333",
        )

        r = await client.get("/api/v1/stats/yearly?year=2026", headers=_auth(admin_token))
        data = r.json()
        # 送课到社区
        songke = next(i for i in data["items"] if i["label"] == "送课到社区")
        assert songke["session_count"] == 2
        assert songke["participant_count"] == 50
        # 党建组
        dangjian = next(i for i in data["items"] if i["label"] == "党建组")
        assert dangjian["session_count"] == 1
        assert dangjian["participant_count"] == 15
        # 总场次
        assert data["total_sessions"] == 3
        assert data["total_participants"] == 65

    @pytest.mark.asyncio
    async def test_only_approved_counted(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        # 创建但只到 pending_community 状态
        headers = _auth(admin_token)
        r = await client.post(
            "/api/v1/members",
            json={"name": "X", "phone": "13800001111", "branch_id": sample_data["branch_id"]},
            headers=headers,
        )
        mid = r.json()["id"]
        r = await client.post(
            "/api/v1/activities",
            json={
                "organizer_branch_id": sample_data["branch_id"],
                "training_at": "2026-05-01T10:00:00",
                "location": "X",
                "theme": "未通过",
                "participant_count": 10,
                "online_offline": "offline",
                "is_centralized": True,
                "is_innovation_theory": True,
                "source_type": "self_organize",
                "audience_category": "community_member",
                "study_hours": 4.0,
                "participants": [{"member_id": mid, "study_hours": 4.0, "attendance_status": "signed"}],
                "photo_count": 1,
            },
            headers=headers,
        )
        aid = r.json()["id"]
        await client.post(
            f"/api/v1/activities/{aid}/attachments",
            json={"kind": "photo", "file_url": "https://x.com/p.jpg"},
            headers=headers,
        )
        await client.post(f"/api/v1/activities/{aid}/submit", headers=headers)
        # 不审批

        r = await client.get("/api/v1/stats/yearly?year=2026", headers=_auth(admin_token))
        data = r.json()
        assert data["total_sessions"] == 0  # 不应计入

    @pytest.mark.asyncio
    async def test_export_xlsx(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        await _create_approved_activity(client, admin_token, sample_data, participant_count=20)

        r = await client.get(
            "/api/v1/stats/yearly/export?year=2026",
            headers=_auth(admin_token),
        )
        assert r.status_code == 200
        assert "spreadsheet" in r.headers["content-type"]
        assert len(r.content) > 1000
        # 文件名
        cd = r.headers["content-disposition"]
        assert "yearly_stats_2026.xlsx" in cd

    @pytest.mark.asyncio
    async def test_year_filter(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        # 2025 年的活动不应计入 2026
        await _create_approved_activity(client, admin_token, sample_data)
        # 但实际数据是 2026-04-09，所以 2025 应该为 0
        r = await client.get("/api/v1/stats/yearly?year=2025", headers=_auth(admin_token))
        data = r.json()
        assert data["total_sessions"] == 0
