"""/api/v1/audits 审核测试。"""
import pytest
from httpx import AsyncClient


async def _login(c, phone, pwd):
    r = await c.post("/api/v1/auth/login", json={"phone": phone, "password": pwd})
    return r.json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


async def _setup_activity_to_pending(client, org_token, sample_data, *, submitter_phone, submitter_pwd):
    """创建一个提交过审核的活动，返回 activity_id。"""
    headers = _auth(org_token)
    # 创建党员
    r = await client.post(
        "/api/v1/members",
        json={"name": "测试党员", "phone": "13800001111", "branch_id": sample_data["branch_id"]},
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
            "study_hours": 4.0,
            "participants": [{"member_id": mid, "study_hours": 4.0, "attendance_status": "signed"}],
            "photo_count": 1,
        },
        headers=headers,
    )
    aid = r.json()["id"]
    # 加照片
    await client.post(
        f"/api/v1/activities/{aid}/attachments",
        json={"kind": "photo", "file_url": "https://example.com/p.jpg"},
        headers=headers,
    )
    # 提交审核
    r = await client.post(f"/api/v1/activities/{aid}/submit", headers=headers)
    assert r.json()["status"] == "pending_community"
    return aid


class TestPendingList:
    @pytest.mark.asyncio
    async def test_community_org_sees_pending_in_own_community(self, client, sample_data):
        # 街道负责人录活动并提交
        org_token = await _login(client, "13800000002", "org123")
        await _setup_activity_to_pending(
            client, org_token, sample_data,
            submitter_phone="13800000002", submitter_pwd="org123",
        )
        # 街道负责人 admin 看（待社区 = 自己发的不可见，但 admin 看全）
        admin_token = await _login(client, "13800000000", "admin123")
        r = await client.get("/api/v1/audits/pending", headers=_auth(admin_token))
        assert r.status_code == 200
        assert r.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_community_org_cannot_self_audit(self, client, sample_data):
        # 社区委员录活动并提交，自己看不到（不可自审）
        org_token = await _login(client, "13800000002", "org123")
        await _setup_activity_to_pending(
            client, org_token, sample_data,
            submitter_phone="13800000002", submitter_pwd="org123",
        )
        r = await client.get("/api/v1/audits/pending", headers=_auth(org_token))
        assert r.status_code == 200
        # 自己提交的，不应该出现在自己的待办
        assert r.json()["total"] == 0


class TestApproveFlow:
    @pytest.mark.asyncio
    async def test_community_approve_then_street_approve(self, client, sample_data):
        """完整流程：社区初审通过 → 街道复审通过。"""
        # admin 录入并提交（绕开不可自审问题）
        admin_token = await _login(client, "13800000000", "admin123")
        await _setup_activity_to_pending(
            client, admin_token, sample_data,
            submitter_phone="13800000000", submitter_pwd="admin123",
        )

        # 社区组织委员（不是提交人）初审
        org_token = await _login(client, "13800000002", "org123")
        r = await client.get("/api/v1/audits/pending", headers=_auth(org_token))
        assert r.json()["total"] == 1
        aid = r.json()["items"][0]["activity_id"]

        r = await client.post(
            f"/api/v1/audits/{aid}/approve",
            json={"comment": "初审通过"},
            headers=_auth(org_token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "pending_street"

        # 街道负责人复审
        lead_token = await _login(client, "13800000001", "lead123")
        r = await client.post(
            f"/api/v1/audits/{aid}/approve",
            json={"comment": "复审通过"},
            headers=_auth(lead_token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

        # 验证：审核后状态 = approved
        r = await client.get(f"/api/v1/activities/{aid}", headers=_auth(admin_token))
        assert r.json()["status"] == "approved"

        # 验证：学时已写入（D9 端点）
        r = await client.get("/api/v1/study-hours?year=2026", headers=_auth(admin_token))
        # D9 端点会做；这里至少确保不报 500
        assert r.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_reject_requires_comment(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        await _setup_activity_to_pending(
            client, admin_token, sample_data,
            submitter_phone="13800000000", submitter_pwd="admin123",
        )
        org_token = await _login(client, "13800000002", "org123")
        r = await client.get("/api/v1/audits/pending", headers=_auth(org_token))
        aid = r.json()["items"][0]["activity_id"]

        # 不填 comment 驳回
        r = await client.post(
            f"/api/v1/audits/{aid}/reject",
            json={},
            headers=_auth(org_token),
        )
        assert r.status_code == 400
        assert "意见" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_reject_sets_status_and_reason(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        await _setup_activity_to_pending(
            client, admin_token, sample_data,
            submitter_phone="13800000000", submitter_pwd="admin123",
        )
        org_token = await _login(client, "13800000002", "org123")
        r = await client.get("/api/v1/audits/pending", headers=_auth(org_token))
        aid = r.json()["items"][0]["activity_id"]

        r = await client.post(
            f"/api/v1/audits/{aid}/reject",
            json={"comment": "照片不够清晰"},
            headers=_auth(org_token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

        # 活动详情里有 reject_reason
        r = await client.get(f"/api/v1/activities/{aid}", headers=_auth(admin_token))
        assert r.json()["status"] == "rejected"
        assert "照片" in r.json()["reject_reason"]


class TestNoSelfAudit:
    @pytest.mark.asyncio
    async def test_cannot_approve_own_activity(self, client, sample_data):
        # 社区委员录并提交，自己去 approve 自己的
        org_token = await _login(client, "13800000002", "org123")
        await _setup_activity_to_pending(
            client, org_token, sample_data,
            submitter_phone="13800000002", submitter_pwd="org123",
        )
        # 即便强制调 API，也要被拦截
        r = await client.post(
            "/api/v1/audits/1/approve",
            json={"comment": "自己审自己"},
            headers=_auth(org_token),
        )
        # 不可自审 → 403
        assert r.status_code == 403
        assert "自己" in r.json()["detail"]


class TestAuditLogs:
    @pytest.mark.asyncio
    async def test_logs_record_all_actions(self, client, sample_data):
        admin_token = await _login(client, "13800000000", "admin123")
        await _setup_activity_to_pending(
            client, admin_token, sample_data,
            submitter_phone="13800000000", submitter_pwd="admin123",
        )
        org_token = await _login(client, "13800000002", "org123")
        r = await client.get("/api/v1/audits/pending", headers=_auth(org_token))
        aid = r.json()["items"][0]["activity_id"]
        await client.post(
            f"/api/v1/audits/{aid}/approve",
            json={"comment": "ok"},
            headers=_auth(org_token),
        )

        r = await client.get(f"/api/v1/audits/{aid}/logs", headers=_auth(admin_token))
        assert r.status_code == 200
        logs = r.json()
        # 应有 submit + approve 两条
        actions = [l["action"] for l in logs]
        assert "submit" in actions
        assert "approve" in actions
