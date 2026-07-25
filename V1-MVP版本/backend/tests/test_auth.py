"""/api/v1/auth 端点测试。"""
import pytest
from httpx import AsyncClient


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, sample_data):
        r = await client.post(
            "/api/v1/auth/login",
            json={"phone": "13800000000", "password": "admin123"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 120 * 60

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, sample_data):
        r = await client.post(
            "/api/v1/auth/login",
            json={"phone": "13800000000", "password": "wrongpwd"},
        )
        assert r.status_code == 401
        assert r.json()["detail"] == "手机号或密码错误"

    @pytest.mark.asyncio
    async def test_login_phone_not_found(self, client: AsyncClient, sample_data):
        r = await client.post(
            "/api/v1/auth/login",
            json={"phone": "13900000000", "password": "admin123"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_login_invalid_phone_format(self, client: AsyncClient, sample_data):
        r = await client.post(
            "/api/v1/auth/login",
            json={"phone": "123", "password": "admin123"},
        )
        # Pydantic 422
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_login_password_too_short(self, client: AsyncClient, sample_data):
        r = await client.post(
            "/api/v1/auth/login",
            json={"phone": "13800000000", "password": "123"},
        )
        assert r.status_code == 422


class TestMe:
    @pytest.mark.asyncio
    async def test_me_success(self, client: AsyncClient, sample_data):
        # 先登录拿 token
        login_r = await client.post(
            "/api/v1/auth/login",
            json={"phone": "13800000000", "password": "admin123"},
        )
        token = login_r.json()["access_token"]

        r = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["phone"] == "13800000000"
        assert data["name"] == "系统管理员"
        assert data["role"] == "system_admin"

    @pytest.mark.asyncio
    async def test_me_no_token(self, client: AsyncClient, sample_data):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, client: AsyncClient, sample_data):
        r = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert r.status_code == 401


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient, sample_data):
        # 登录拿 refresh
        login_r = await client.post(
            "/api/v1/auth/login",
            json={"phone": "13800000000", "password": "admin123"},
        )
        refresh = login_r.json()["refresh_token"]

        r = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_should_fail(self, client: AsyncClient, sample_data):
        """用 access token 去 refresh 应该失败（type 校验）。"""
        login_r = await client.post(
            "/api/v1/auth/login",
            json={"phone": "13800000000", "password": "admin123"},
        )
        access = login_r.json()["access_token"]

        r = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient, sample_data):
        r = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "garbage"},
        )
        assert r.status_code == 401


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient, sample_data):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
