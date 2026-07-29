# -*- coding: utf-8 -*-
"""
v3 改造 activities.py（基于 .bak）。所有改动都用精确字符串替换，确保缩进/编码正确。
"""
import os
import re

BACKUP = r'E:\new party\nw-party-prototype\V1-MVP版本\backend\app\api\v1\activities.py.bak'
TARGET = r'E:\new party\nw-party-prototype\V1-MVP版本\backend\app\api\v1\activities.py'

with open(BACKUP, 'rb') as f:
    raw = f.read()
src = raw.decode('utf-8')
print(f'Loaded backup: {len(src)} chars')

# 用 CRLF（备份是 \r\n）
NL = '\r\n'

# ===== 模式 1: 6 处 BRANCH_SEC 权限校验（每处 detail 不同） =====
# 用更精确的 pattern：替换为新结构，detail 跟随原 raise 的 detail
pattern_branchsec = re.compile(
    r'( {4})if user\.role == User\.ROLE_BRANCH_SEC and a\.organizer_branch_id != user\.branch_id:\r\n        raise HTTPException\(status_code=403, detail="([^"]+)"\)'
)
def replace_branchsec(m):
    indent = m.group(1)  # 4 空格
    detail = m.group(2)  # 原始 detail 文字
    return (
        f'{indent}if user.role == User.ROLE_BRANCH_SEC:{NL}'
        f'{indent}    # v3: organizer_branch_id 可能为 None（上级送课），用 co_organize_branch_ids 判断{NL}'
        f'{indent}    allowed_branches = set(a.co_organize_branch_ids or []){NL}'
        f'{indent}    if user.branch_id not in allowed_branches:{NL}'
        f'{indent}        raise HTTPException(status_code=403, detail="{detail}")'
    )
src, n1 = pattern_branchsec.subn(replace_branchsec, src)
print(f'Pattern 1 (BRANCH_SEC simple): replaced {n1} times')

# ===== 模式 2: 1 处 BRANCH_SEC + MEMBER（get_activity 内） =====
pattern_branchmem = re.compile(
    r'( {4})if user\.role in \(User\.ROLE_BRANCH_SEC, User\.ROLE_MEMBER\) and a\.organizer_branch_id != user\.branch_id:\r\n        raise HTTPException\(status_code=403, detail="([^"]+)"\)'
)
def replace_branchmem(m):
    indent = m.group(1)
    detail = m.group(2)
    return (
        f'{indent}if user.role in (User.ROLE_BRANCH_SEC, User.ROLE_MEMBER):{NL}'
        f'{indent}    # v3: organizer_branch_id 可能为 None（上级送课），用 co_organize_branch_ids 判断{NL}'
        f'{indent}    allowed_branches = set(a.co_organize_branch_ids or []){NL}'
        f'{indent}    if user.branch_id not in allowed_branches:{NL}'
        f'{indent}        raise HTTPException(status_code=403, detail="{detail}")'
    )
src, n2 = pattern_branchmem.subn(replace_branchmem, src)
print(f'Pattern 2 (BRANCH_SEC + MEMBER): replaced {n2} times')

# ===== create_activity 段 =====
old_create = (
    f'    # 校验支部存在 + 权限{NL}'
    f'    br_r = await db.execute(select(Branch).where(Branch.id == body.organizer_branch_id)){NL}'
    f'    branch = br_r.scalar_one_or_none(){NL}'
    f'    if not branch:{NL}'
    f'        raise HTTPException(status_code=400, detail="支部不存在"){NL}'
    f'    if user.role == User.ROLE_COMMUNITY_ORG and user.community_id != branch.community_id:{NL}'
    f'        raise HTTPException(status_code=403, detail="无权在该支部录入"){NL}'
    f'    if user.role == User.ROLE_BRANCH_SEC and user.branch_id != body.organizer_branch_id:{NL}'
    f'        raise HTTPException(status_code=403, detail="只能在本支部录入活动"){NL}'
    f'{NL}'
    f'    # 自动从支部得到 community_id{NL}'
    f'    community_id = branch.community_id{NL}'
    f'{NL}'
    f'    # 校验照片至少 1 张（D6 阶段；当前只校验字段）{NL}'
    f'    if body.photo_count < 1:{NL}'
    f'        # 注意：photo_count 客户端上传后才知道，这里只是软校验{NL}'
    f'        # 实际校验在提交审核（submit）时做{NL}'
    f'        pass{NL}'
    f'{NL}'
    f'    # 创建活动{NL}'
    f'    data = body.model_dump(exclude={{"participants", "photo_count"}}){NL}'
    f'    activity = Activity(**data, created_by=user.id, status="draft", community_id=community_id)'
)
new_create = (
    f'    # v3: 举办方式改为 organize_type + co_organize_branch_ids（自行组织时填） / upper_org（上级送课时填）。{NL}'
    f'    # community_id 仍然必填冗余，从 co_organize_branch_ids[0] 反查得到。{NL}'
    f'    # organizer_branch_id 仅做审计占位（取 co_organize_branch_ids[0]）。{NL}'
    f'    community_id: int | None = None{NL}'
    f'    organizer_branch_id: int | None = None{NL}'
    f'{NL}'
    f'    if body.organize_type == "self_organize":{NL}'
    f'        # 校验协办支部：全部存在 + 同一社区{NL}'
    f'        if not body.co_organize_branch_ids:{NL}'
    f'            raise HTTPException(status_code=400, detail="自行组织必须选择至少 1 个协办支部"){NL}'
    f'        brs_r = await db.execute({NL}'
    f'            select(Branch).where(Branch.id.in_(body.co_organize_branch_ids)){NL}'
    f'        ){NL}'
    f'        branches = brs_r.scalars().all(){NL}'
    f'        if len(branches) != len(set(body.co_organize_branch_ids)):{NL}'
    f'            raise HTTPException(status_code=400, detail="部分协办支部不存在"){NL}'
    f'        community_ids = {{b.community_id for b in branches}}{NL}'
    f'        if len(community_ids) != 1:{NL}'
    f'            raise HTTPException(status_code=400, detail="所有协办支部必须在同一社区"){NL}'
    f'        community_id = community_ids.pop(){NL}'
    f'        # 兼容老字段：organizer_branch_id 记第一个{NL}'
    f'        organizer_branch_id = body.co_organize_branch_ids[0]{NL}'
    f'        # 角色权限校验（只校验社区级，街道级全看）{NL}'
    f'        if user.role == User.ROLE_COMMUNITY_ORG and user.community_id != community_id:{NL}'
    f'            raise HTTPException(status_code=403, detail="无权在该社区录入"){NL}'
    f'        if user.role == User.ROLE_BRANCH_SEC:{NL}'
    f'            if user.branch_id not in body.co_organize_branch_ids:{NL}'
    f'                raise HTTPException(status_code=403, detail="只能在本支部录入活动"){NL}'
    f'    else:  # upper_send{NL}'
    f'        if not body.upper_org or not body.upper_org.strip():{NL}'
    f'            raise HTTPException(status_code=400, detail="上级送课必须填写具体部门"){NL}'
    f'        # 上级送课：community_id 从创建者上下文推（默认放创建者所在社区，否则取第一社区）{NL}'
    f'        if user.community_id:{NL}'
    f'            community_id = user.community_id{NL}'
    f'        else:{NL}'
    f'            # 兜底：取第一社区{NL}'
    f'            r = await db.execute(select(Community).order_by(Community.id).limit(1)){NL}'
    f'            c = r.scalar_one_or_none(){NL}'
    f'            community_id = c.id if c else 1{NL}'
    f'        organizer_branch_id = None{NL}'
    f'{NL}'
    f'    if community_id is None:{NL}'
    f'        raise HTTPException(status_code=400, detail="无法确定社区"){NL}'
    f'{NL}'
    f'    # 校验照片至少 1 张（D6 阶段；当前只校验字段）{NL}'
    f'    if body.photo_count < 1:{NL}'
    f'        pass{NL}'
    f'{NL}'
    f'    # 创建活动{NL}'
    f'    data = body.model_dump({NL}'
    f'        exclude={{"participants", "photo_count", "organizer_branch_id"}},{NL}'
    f'    ){NL}'
    f'    activity = Activity({NL}'
    f'        **data,{NL}'
    f'        created_by=user.id,{NL}'
    f'        status="draft",{NL}'
    f'        community_id=community_id,{NL}'
    f'        organizer_branch_id=organizer_branch_id,{NL}'
    f'        source_type=body.organize_type,  # 兼容老字段{NL}'
    f'    )'
)
n3 = src.count(old_create)
print(f'create_activity block: {n3} times')
if n3 != 1:
    raise SystemExit(f'create_activity expected 1, got {n3}')
src = src.replace(old_create, new_create)

# ===== update_activity 段 =====
old_update = (
    f'    data = body.model_dump(exclude_unset=True, exclude={{"participants"}}){NL}'
    f'    for k, v in data.items():{NL}'
    f'        setattr(a, k, v)'
)
new_update = (
    f'    data = body.model_dump(exclude_unset=True, exclude={{"participants", "organizer_branch_id"}}){NL}'
    f'    # v3: 当 organize_type=self_organize 且协办支部变化时，重算 organizer_branch_id + community_id{NL}'
    f'    if "organize_type" in data or "co_organize_branch_ids" in data:{NL}'
    f'        # 取最新值（DB 已 set，但还没 commit；用 a 当前属性）{NL}'
    f'        new_org_type = data.get("organize_type", a.organize_type){NL}'
    f'        if new_org_type == "self_organize":{NL}'
    f'            new_co_ids = data.get("co_organize_branch_ids", list(a.co_organize_branch_ids or [])){NL}'
    f'            if new_co_ids:{NL}'
    f'                brs_r = await db.execute({NL}'
    f'                    select(Branch).where(Branch.id.in_(new_co_ids)){NL}'
    f'                ){NL}'
    f'                branches = brs_r.scalars().all(){NL}'
    f'                community_ids = {{b.community_id for b in branches}}{NL}'
    f'                if len(community_ids) == 1:{NL}'
    f'                    a.community_id = community_ids.pop(){NL}'
    f'                a.organizer_branch_id = new_co_ids[0]{NL}'
    f'                a.source_type = "self_organize"{NL}'
    f'                a.upper_org = None{NL}'
    f'        elif new_org_type == "upper_send":{NL}'
    f'            a.organizer_branch_id = None{NL}'
    f'            a.source_type = "upper_send"{NL}'
    f'            a.co_organize_branch_ids = []{NL}'
    f'    for k, v in data.items():{NL}'
    f'        setattr(a, k, v)'
)
n4 = src.count(old_update)
print(f'update_activity block: {n4} times')
if n4 != 1:
    raise SystemExit(f'update_activity expected 1, got {n4}')
src = src.replace(old_update, new_update)

# ===== 写文件 (UTF-8 无 BOM) =====
out_bytes = src.encode('utf-8')
with open(TARGET, 'wb') as f:
    f.write(out_bytes)
print(f'Written: {len(out_bytes)} bytes (no BOM)')

# 验证
import ast
try:
    ast.parse(src)
    print('AST parse OK')
except SyntaxError as e:
    print(f'AST SYNTAX ERROR at line {e.lineno}: {e.msg}')
    print(f'  text: {e.text!r}')
    # 打印上下文
    lines = src.split('\n')
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+3)):
        print(f'  L{i+1}: {lines[i]!r}')
