"""/api/v1/orgs 端点测试。"""
import pytest
from httpx import AsyncClient


async def _login(client: AsyncClient, phone: str, password: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"phone": phone, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


class TestOrgs:
    @pytest.mark.asyncio
    async def test_list_streets_requires_auth(self, client: AsyncClient, sample_data):
        r = await client.get("/api/v1/orgs/streets")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_list_streets(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.get(
            "/api/v1/orgs/streets",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["name"] == "南湾街道"

    @pytest.mark.asyncio
    async def test_list_communities_filtered_by_street(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.get(
            f"/api/v1/orgs/communities?street_id={sample_data['street_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["name"] == "南湾社区"

    @pytest.mark.asyncio
    async def test_list_branches_filtered_by_community(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.get(
            f"/api/v1/orgs/branches?community_id={sample_data['community_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["name"] == "南湾社区第一党支部"

    @pytest.mark.asyncio
    async def test_org_tree(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.get(
            "/api/v1/orgs/tree",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        street = data[0]
        assert street["name"] == "南湾街道"
        assert len(street["communities"]) == 1
        community = street["communities"][0]
        assert community["name"] == "南湾社区"
        assert len(community["branches"]) == 1
        assert community["branches"][0]["name"] == "南湾社区第一党支部"

    @pytest.mark.asyncio
    async def test_my_scope_street_lead(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000001", "lead123")
        r = await client.get(
            "/api/v1/orgs/my-scope",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["scope"] == "street"
        assert data["street_id"] == sample_data["street_id"]

    @pytest.mark.asyncio
    async def test_my_scope_community_org(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000002", "org123")
        r = await client.get(
            "/api/v1/orgs/my-scope",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["scope"] == "community"
        assert data["community_id"] == sample_data["community_id"]
