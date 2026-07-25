"""
党员批量导入：从 xlsx 解析 + 校验 + 写入。

策略（全有全无 v1）：
- 任一行失败 → 整文件回滚
- 详细错误：行号 + 错误码 + 错误描述
"""
import io
import re
from dataclasses import dataclass, field
from datetime import date
from typing import BinaryIO

from openpyxl import Workbook, load_workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member import Member
from app.models.party import Branch
from app.models.user import User
from app.services.permissions import can_create_member_in


REQUIRED_HEADERS = ["支部名称", "姓名", "手机号"]


@dataclass
class ImportError:
    row: int
    phone: str | None
    errors: list[str] = field(default_factory=list)


@dataclass
class ImportResult:
    total_rows: int = 0
    success_rows: int = 0
    failed_rows: int = 0
    error_log: list[ImportError] = field(default_factory=list)


def _validate_phone(v: str) -> str | None:
    v = (v or "").strip()
    if not v:
        return "手机号为空"
    if not re.match(r"^1[3-9]\d{9}$", v):
        return f"手机号格式错误: {v}"
    return None


def _validate_name(v: str) -> str | None:
    v = (v or "").strip()
    if not v:
        return "姓名为空"
    if len(v) > 64:
        return f"姓名超过 64 字符: {v[:32]}..."
    return None


def _validate_id_card(v: str) -> str | None:
    v = (v or "").strip()
    if not v:
        return None
    if not re.match(r"^\d{17}[\dXx]$", v):
        return f"身份证号格式错误"
    return None


def _validate_gender(v: str) -> str | None:
    v = (v or "").strip()
    if not v:
        return None
    if v not in ("男", "女", "其他", "male", "female", "other"):
        return f"性别不在枚举: {v}"
    return None


def _normalize_gender(v: str) -> str | None:
    v = (v or "").strip()
    if not v:
        return None
    return {"男": "male", "女": "female", "其他": "other"}.get(v, v)


def _parse_date(v) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            return None
    return None


def _validate_status(v: str) -> str | None:
    v = (v or "").strip()
    if not v:
        return None
    mapping = {"在职": "active", "转入": "transferred", "转出": "dimission", "预备": "active"}
    if v not in mapping:
        return f"状态不在枚举: {v}"
    return None


def _normalize_status(v: str) -> str:
    v = (v or "").strip()
    return {"在职": "active", "转入": "transferred", "转出": "dimission", "预备": "active"}.get(v, v or "active")


def generate_template_xlsx() -> bytes:
    """生成导入模板 xlsx。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "党员信息"

    headers = ["支部名称", "姓名", "手机号", "身份证号", "性别", "入党时间", "状态"]
    ws.append(headers)

    # 示例行
    ws.append(["南湾社区第一党支部", "张三", "13800001111", "440307199001011234", "男", "2019-03-15", "在职"])
    ws.append(["南湾社区第一党支部", "李四", "13800002222", "", "女", "", "预备"])

    # 表头样式
    from openpyxl.styles import Font, PatternFill, Alignment
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="B22222", end_color="B22222", fill_type="solid")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # 列宽
    for col, w in zip("ABCDEFG", [22, 12, 14, 22, 10, 14, 10]):
        ws.column_dimensions[col].width = w

    # 备注行
    ws.append([])  # 空行
    note = ws.cell(row=ws.max_row + 1, column=1, value="说明：请删除示例行后填入真实数据；支部名称必须与系统一致；手机号必须 11 位。")
    note.font = Font(italic=True, color="888888")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def parse_and_import(
    db: AsyncSession,
    file_bytes: bytes,
    user: User,
) -> ImportResult:
    """解析 xlsx + 校验 + 写入。任一失败则全部回滚。"""
    result = ImportResult()

    try:
        wb = load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
    except Exception as e:
        result.error_log.append(ImportError(row=0, phone=None, errors=[f"xlsx 解析失败: {e}"]))
        result.failed_rows = 1
        return result

    ws = wb.active
    if not ws:
        result.error_log.append(ImportError(row=0, phone=None, errors=["空文件"]))
        result.failed_rows = 1
        return result

    # 1. 校验表头
    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if not header_row:
        result.error_log.append(ImportError(row=0, phone=None, errors=["文件无表头"]))
        result.failed_rows = 1
        return result

    headers = [str(c).strip() if c else "" for c in header_row]
    if not all(h in headers for h in REQUIRED_HEADERS):
        missing = [h for h in REQUIRED_HEADERS if h not in headers]
        result.error_log.append(ImportError(row=0, phone=None, errors=[f"表头缺少必填列: {missing}"]))
        result.failed_rows = 1
        return result

    # 2. 缓存已存在的手机号 + 支部映射
    branch_name_to_id: dict[str, int] = {}
    br_r = await db.execute(select(Branch))
    for b in br_r.scalars().all():
        branch_name_to_id[b.name] = b.id

    existing_phones: set[str] = set()
    ph_r = await db.execute(select(Member.phone).where(Member.status == "active"))
    for (p,) in ph_r.all():
        existing_phones.add(p)

    # 3. 逐行校验
    rows_to_insert: list[Member] = []
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # 跳过空行
        if not any(c for c in row):
            continue
        result.total_rows += 1

        # 列对齐
        row_data = {h: row[idx] if idx < len(row) else None for idx, h in enumerate(headers)}
        errors: list[str] = []
        phone_raw = str(row_data.get("手机号") or "").strip()

        # 校验
        branch_name = str(row_data.get("支部名称") or "").strip()
        if not branch_name:
            errors.append("支部名称为空")
        elif branch_name not in branch_name_to_id:
            errors.append(f"支部不存在: {branch_name}")

        e = _validate_name(str(row_data.get("姓名") or ""))
        if e:
            errors.append(e)

        e = _validate_phone(phone_raw)
        if e:
            errors.append(e)
        elif phone_raw in existing_phones:
            errors.append(f"手机号已存在: {phone_raw}")
        elif phone_raw in {str(getattr(r, "phone", "")) for r in rows_to_insert}:
            errors.append(f"文件内重复手机号: {phone_raw}")

        e = _validate_id_card(str(row_data.get("身份证号") or ""))
        if e:
            errors.append(e)

        e = _validate_gender(str(row_data.get("性别") or ""))
        if e:
            errors.append(e)

        e = _validate_status(str(row_data.get("状态") or ""))
        if e:
            errors.append(e)

        if errors:
            result.error_log.append(ImportError(row=i, phone=phone_raw or None, errors=errors))
            result.failed_rows += 1
        else:
            # 权限校验：检查 user 能否在该支部新增
            branch_id = branch_name_to_id[branch_name]
            br = await db.get(Branch, branch_id)
            if not br or not can_create_member_in(user, br.community_id):
                result.error_log.append(
                    ImportError(row=i, phone=phone_raw, errors=[f"无权在支部 {branch_name} 新增"])
                )
                result.failed_rows += 1
                continue

            member = Member(
                branch_id=branch_id,
                name=str(row_data.get("姓名") or "").strip(),
                phone=phone_raw,
                id_card_no=str(row_data.get("身份证号") or "").strip() or None,
                gender=_normalize_gender(str(row_data.get("性别") or "")),
                join_date=_parse_date(row_data.get("入党时间")),
                status=_normalize_status(str(row_data.get("状态") or "")),
                created_by=user.id,
            )
            rows_to_insert.append(member)
            existing_phones.add(phone_raw)

    # 4. 全有全无：任一失败则全部不入库
    if result.failed_rows > 0:
        return result

    # 5. 批量插入
    try:
        db.add_all(rows_to_insert)
        await db.commit()
        result.success_rows = len(rows_to_insert)
    except Exception as e:
        await db.rollback()
        result.error_log.append(ImportError(row=0, phone=None, errors=[f"批量插入失败: {e}"]))
        result.failed_rows = result.total_rows
        result.success_rows = 0

    return result
