"""/api/v1/dicts 字典测试。"""
import pytest
from httpx import AsyncClient


async def _login(c, phone, pwd):
    r = await c.post("/api/v1/auth/login", json={"phone": phone, "password": pwd})
    return r.json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


class TestLecturers:
    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.get("/api/v1/dicts/lecturers", headers=_auth(token))
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_create_lecturer_admin(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.post(
            "/api/v1/dicts/lecturers",
            json={"name": "龚建华", "intro": "党建专家"},
            headers=_auth(token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "龚建华"

    @pytest.mark.asyncio
    async def test_create_lecturer_community_org_forbidden(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        r = await client.post(
            "/api/v1/dicts/lecturers",
            json={"name": "张三"},
            headers=_auth(token),
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_create_lecturer_street_lead(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000001", "lead123")
        r = await client.post(
            "/api/v1/dicts/lecturers",
            json={"name": "李四", "intro": "教授"},
            headers=_auth(token),
        )
        assert r.status_code == 201

    @pytest.mark.asyncio
    async def test_update_lecturer(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        c = await client.post(
            "/api/v1/dicts/lecturers", json={"name": "张三"}, headers=_auth(token)
        )
        lid = c.json()["id"]
        r = await client.patch(
            f"/api/v1/dicts/lecturers/{lid}",
            json={"intro": "更新介绍"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["intro"] == "更新介绍"

    @pytest.mark.asyncio
    async def test_delete_lecturer_soft(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        c = await client.post(
            "/api/v1/dicts/lecturers", json={"name": "张三"}, headers=_auth(token)
        )
        lid = c.json()["id"]
        r = await client.delete(f"/api/v1/dicts/lecturers/{lid}", headers=_auth(token))
        assert r.status_code == 204
        # 仍然在列表里但 status=inactive
        r2 = await client.get("/api/v1/dicts/lecturers", headers=_auth(token))
        item = next(x for x in r2.json() if x["id"] == lid)
        assert item["status"] == "inactive"


class TestCategories:
    @pytest.mark.asyncio
    async def test_list_has_seeds(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.get("/api/v1/dicts/training-categories", headers=_auth(token))
        assert r.status_code == 200
        codes = [x["code"] for x in r.json()]
        # 种子数据里有的
        assert "community_member" in codes

    @pytest.mark.asyncio
    async def test_create_category_only_admin(self, client: AsyncClient, sample_data):
        # 社区委员不能新增
        token = await _login(client, "13800000002", "org123")
        r = await client.post(
            "/api/v1/dicts/training-categories",
            json={"code": "test", "name": "测试"},
            headers=_auth(token),
        )
        assert r.status_code == 403

        # 超管可以
        token = await _login(client, "13800000000", "admin123")
        r = await client.post(
            "/api/v1/dicts/training-categories",
            json={"code": "test_category", "name": "测试类别"},
            headers=_auth(token),
        )
        assert r.status_code == 201


class TestSources:
    @pytest.mark.asyncio
    async def test_list_has_seeds(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.get("/api/v1/dicts/training-sources", headers=_auth(token))
        assert r.status_code == 200
        codes = [x["code"] for x in r.json()]
        assert "upper_send" in codes
        assert "self_organize" in codes
