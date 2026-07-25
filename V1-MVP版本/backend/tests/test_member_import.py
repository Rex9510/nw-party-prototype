"""/api/v1/members/import 批量导入测试。"""
import io

import pytest
from httpx import AsyncClient
from openpyxl import Workbook

from app.services.member_import import generate_template_xlsx


async def _login(c, phone, pwd):
    r = await c.post("/api/v1/auth/login", json={"phone": phone, "password": pwd})
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _make_xlsx(rows: list[list]) -> bytes:
    """生成 xlsx bytes。"""
    wb = Workbook()
    ws = wb.active
    ws.append(["支部名称", "姓名", "手机号", "身份证号", "性别", "入党时间", "状态"])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestTemplate:
    @pytest.mark.asyncio
    async def test_download_template_requires_auth(self, client: AsyncClient, sample_data):
        r = await client.get("/api/v1/members/template")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_download_template(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.get("/api/v1/members/template", headers=_auth(token))
        assert r.status_code == 200
        assert "spreadsheet" in r.headers["content-type"]
        # 能直接调用 generate_template_xlsx
        content = generate_template_xlsx()
        assert len(content) > 1000


class TestImport:
    @pytest.mark.asyncio
    async def test_import_requires_auth(self, client: AsyncClient, sample_data):
        xlsx = _make_xlsx([])
        r = await client.post(
            "/api/v1/members/import",
            files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_import_success(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        xlsx = _make_xlsx([
            ["南湾社区第一党支部", "张三", "13800001111", "", "男", "2019-03-15", "在职"],
            ["南湾社区第一党支部", "李四", "13800002222", "", "女", "", "预备"],
        ])
        r = await client.post(
            "/api/v1/members/import",
            files={"file": ("members.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=_auth(token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total_rows"] == 2
        assert data["success_rows"] == 2
        assert data["failed_rows"] == 0

        # 验证数据库
        r2 = await client.get("/api/v1/members", headers=_auth(token))
        assert r2.json()["total"] == 2

    @pytest.mark.asyncio
    async def test_import_invalid_phone_rollback(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        xlsx = _make_xlsx([
            ["南湾社区第一党支部", "张三", "13800001111", "", "男", "", "在职"],
            ["南湾社区第一党支部", "李四", "12345", "", "女", "", "在职"],  # 手机号错
        ])
        r = await client.post(
            "/api/v1/members/import",
            files={"file": ("members.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=_auth(token),
        )
        assert r.status_code == 200
        data = r.json()
        # 全有全无：第二条失败 → 整文件回滚，无任何入库
        assert data["success_rows"] == 0
        assert data["failed_rows"] >= 1
        assert any("格式" in str(e) for e in data["error_log"])

        # 验证：数据库无任何新数据
        r2 = await client.get("/api/v1/members", headers=_auth(token))
        assert r2.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_import_branch_not_found(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        xlsx = _make_xlsx([
            ["不存在的支部", "张三", "13800001111", "", "男", "", "在职"],
        ])
        r = await client.post(
            "/api/v1/members/import",
            files={"file": ("members.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=_auth(token),
        )
        data = r.json()
        assert data["failed_rows"] == 1
        assert "支部不存在" in str(data["error_log"])

    @pytest.mark.asyncio
    async def test_import_duplicate_phone_in_file(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        xlsx = _make_xlsx([
            ["南湾社区第一党支部", "张三", "13800001111", "", "男", "", "在职"],
            ["南湾社区第一党支部", "李四", "13800001111", "", "女", "", "在职"],  # 重复
        ])
        r = await client.post(
            "/api/v1/members/import",
            files={"file": ("members.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=_auth(token),
        )
        data = r.json()
        # 第二条检测到文件内重复，失败 → 整文件回滚
        assert data["success_rows"] == 0
        assert data["failed_rows"] >= 1

    @pytest.mark.asyncio
    async def test_import_invalid_file_type(self, client: AsyncClient, sample_data):
        token = await _login(client, "13800000000", "admin123")
        r = await client.post(
            "/api/v1/members/import",
            files={"file": ("test.txt", b"hello", "text/plain")},
            headers=_auth(token),
        )
        assert r.status_code == 400
