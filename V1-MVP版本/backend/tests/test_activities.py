"""/api/v1/activities 活动测试。"""
import pytest
from httpx import AsyncClient


async def _login(c, phone, pwd):
    r = await c.post("/api/v1/auth/login", json={"phone": phone, "password": pwd})
    return r.json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


async def _create_member(client, headers, sample_data, phone, name="测试党员"):
    r = await client.post(
        "/api/v1/members",
        json={"name": name, "phone": phone, "branch_id": sample_data["branch_id"]},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _activity_body(sample_data, member_ids, lecturer_id=None):
    return {
        "organizer_branch_id": sample_data["branch_id"],
        "training_at": "2026-04-09T10:00:00",
        "location": "南湾街道6楼会议室",
        "lecturer_id": lecturer_id,
        "theme": "深入学习贯彻党的二十届四中全会精神专题培训",
        "participant_count": len(member_ids),
        "online_offline": "offline",
        "is_centralized": True,
        "is_innovation_theory": True,
        "source_type": "self_organize",
        "audience_category": "community_member",
        "study_hours": 4.0,
        "participants": [
            {"member_id": mid, "study_hours": 4.0, "attendance_status": "signed"}
            for mid in member_ids
        ],
        "photo_count": 1,
    }


class TestActivityCRUD:
    @pytest.mark.asyncio
    async def test_create_activity(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        headers = _auth(token)
        mid = await _create_member(client, headers, sample_data, "13800001111")
        body = _activity_body(sample_data, [mid])
        r = await client.post("/api/v1/activities", json=body, headers=headers)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["status"] == "draft"
        assert data["theme"] == body["theme"]
        assert len(data["participants"]) == 1

    @pytest.mark.asyncio
    async def test_create_activity_branch_not_found(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        headers = _auth(token)
        body = _activity_body(sample_data, [])
        body["organizer_branch_id"] = 9999
        r = await client.post("/api/v1/activities", json=body, headers=headers)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_create_activity_admin_ok(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        body = _activity_body(sample_data, [])
        body["organizer_branch_id"] = sample_data["branch_id"]
        r = await client.post("/api/v1/activities", json=body, headers=_auth(token))
        assert r.status_code == 201

    @pytest.mark.asyncio
    async def test_list_activities(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        headers = _auth(token)
        mid = await _create_member(client, headers, sample_data, "13800001111")
        body = _activity_body(sample_data, [mid])
        await client.post("/api/v1/activities", json=body, headers=headers)

        r = await client.get("/api/v1/activities", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_get_activity(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        headers = _auth(token)
        mid = await _create_member(client, headers, sample_data, "13800001111")
        body = _activity_body(sample_data, [mid])
        c = await client.post("/api/v1/activities", json=body, headers=headers)
        aid = c.json()["id"]
        r = await client.get(f"/api/v1/activities/{aid}", headers=headers)
        assert r.status_code == 200
        assert r.json()["id"] == aid

    @pytest.mark.asyncio
    async def test_update_activity_draft(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        headers = _auth(token)
        mid = await _create_member(client, headers, sample_data, "13800001111")
        c = await client.post("/api/v1/activities", json=_activity_body(sample_data, [mid]), headers=headers)
        aid = c.json()["id"]
        r = await client.patch(
            f"/api/v1/activities/{aid}",
            json={"location": "新地址"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["location"] == "新地址"

    @pytest.mark.asyncio
    async def test_delete_activity_draft(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        headers = _auth(token)
        mid = await _create_member(client, headers, sample_data, "13800001111")
        c = await client.post("/api/v1/activities", json=_activity_body(sample_data, [mid]), headers=headers)
        aid = c.json()["id"]
        r = await client.delete(f"/api/v1/activities/{aid}", headers=headers)
        assert r.status_code == 204


class TestActivitySubmit:
    @pytest.mark.asyncio
    async def test_submit_without_photo_fails(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        headers = _auth(token)
        mid = await _create_member(client, headers, sample_data, "13800001111")
        c = await client.post("/api/v1/activities", json=_activity_body(sample_data, [mid]), headers=headers)
        aid = c.json()["id"]
        r = await client.post(f"/api/v1/activities/{aid}/submit", headers=headers)
        assert r.status_code == 400
        assert "photo" in r.json()["detail"].lower() or "照片" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_without_participants_fails(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        headers = _auth(token)
        c = await client.post("/api/v1/activities", json=_activity_body(sample_data, []), headers=headers)
        aid = c.json()["id"]
        await client.post(
            f"/api/v1/activities/{aid}/attachments",
            json={"kind": "photo", "file_url": "https://example.com/p1.jpg", "sort": 0},
            headers=headers,
        )
        r = await client.post(f"/api/v1/activities/{aid}/submit", headers=headers)
        assert r.status_code == 400
        assert "人员" in r.json()["detail"] or "participant" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_submit_success(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        headers = _auth(token)
        mid = await _create_member(client, headers, sample_data, "13800001111")
        c = await client.post("/api/v1/activities", json=_activity_body(sample_data, [mid]), headers=headers)
        aid = c.json()["id"]
        await client.post(
            f"/api/v1/activities/{aid}/attachments",
            json={"kind": "photo", "file_url": "https://example.com/p1.jpg"},
            headers=headers,
        )
        r = await client.post(f"/api/v1/activities/{aid}/submit", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "pending_community"
