"""/api/v1/members 端点测试。"""
import pytest
from httpx import AsyncClient


async def _login(client: AsyncClient, phone: str, password: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"phone": phone, "password": password})
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestMembersList:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient, sample_data):
        r = await client.get("/api/v1/members")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.get("/api/v1/members", headers=_auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_admin_can_see_all(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        # 先创建 3 个党员
        for i in range(3):
            await client.post(
                "/api/v1/members",
                json={
                    "name": f"党员{i}",
                    "phone": f"1390000000{i}",
                    "branch_id": sample_data["branch_id"],
                },
                headers=_auth(token),
            )
        r = await client.get("/api/v1/members", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["total"] == 3

    @pytest.mark.asyncio
    async def test_keyword_search(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        await client.post(
            "/api/v1/members",
            json={"name": "张伟", "phone": "13900000001", "branch_id": sample_data["branch_id"]},
            headers=_auth(token),
        )
        await client.post(
            "/api/v1/members",
            json={"name": "李娜", "phone": "13900000002", "branch_id": sample_data["branch_id"]},
            headers=_auth(token),
        )
        r = await client.get("/api/v1/members?keyword=张", headers=_auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "张伟"


class TestMemberCreate:
    @pytest.mark.asyncio
    async def test_create_success(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.post(
            "/api/v1/members",
            json={"name": "张伟", "phone": "13912345678", "branch_id": sample_data["branch_id"]},
            headers=_auth(token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "张伟"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_duplicate_phone(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        body = {"name": "张伟", "phone": "13912345678", "branch_id": sample_data["branch_id"]}
        await client.post("/api/v1/members", json=body, headers=_auth(token))
        r = await client.post("/api/v1/members", json=body, headers=_auth(token))
        assert r.status_code == 400
        assert "phone" in r.json()["detail"].lower() or "exists" in r.json()["detail"].lower() or "已存在" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_invalid_phone(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.post(
            "/api/v1/members",
            json={"name": "张伟", "phone": "123", "branch_id": sample_data["branch_id"]},
            headers=_auth(token),
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_create_branch_not_found(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.post(
            "/api/v1/members",
            json={"name": "张伟", "phone": "13912345678", "branch_id": 9999},
            headers=_auth(token),
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_community_org_can_create_in_own_community(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        r = await client.post(
            "/api/v1/members",
            json={"name": "李娜", "phone": "13912345678", "branch_id": sample_data["branch_id"]},
            headers=_auth(token),
        )
        assert r.status_code == 201


class TestMemberUpdate:
    @pytest.mark.asyncio
    async def test_update_success(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        c = await client.post(
            "/api/v1/members",
            json={"name": "张伟", "phone": "13912345678", "branch_id": sample_data["branch_id"]},
            headers=_auth(token),
        )
        mid = c.json()["id"]
        r = await client.patch(
            f"/api/v1/members/{mid}",
            json={"name": "张大伟"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["name"] == "张大伟"


class TestMemberDelete:
    @pytest.mark.asyncio
    async def test_soft_delete(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        c = await client.post(
            "/api/v1/members",
            json={"name": "张伟", "phone": "13912345678", "branch_id": sample_data["branch_id"]},
            headers=_auth(token),
        )
        mid = c.json()["id"]
        r = await client.delete(f"/api/v1/members/{mid}", headers=_auth(token))
        assert r.status_code == 204

        # 软删除后默认列表不再显示
        r2 = await client.get("/api/v1/members", headers=_auth(token))
        assert r2.json()["total"] == 0
