"""v3: 活动「举办单位」合并为单选 enum + 协办支部多选

Revision ID: 2026_07_28_0002
Revises: 2026_07_28_0001
Create Date: 2026-07-28 10:00:00.000000

改动：
1. activities.organize_type         新增（VARCHAR(16), NOT NULL, default 'self_organize'）
2. activities.co_organize_branch_ids 新增（JSON, NOT NULL, default '[]'）
3. activities.organizer_branch_id   NOT NULL → NULL（保留字段+FK+索引，但前端不再填，做审计）
4. activities.source_type           NOT NULL → NULL（前端用 organize_type 替代，保留字段做兼容）
5. 删 ix_activities_organizer_branch_id 索引（organizer_branch_id 不再用于过滤）

数据迁移：
- source_type=upper_send → organize_type='upper_send'
- source_type=self_organize → organize_type='self_organize'
- 老 self_organize 的 organizer_branch_id（如果非空）→ co_organize_branch_ids = [organizer_branch_id]

策略：动态探测 activities 表的所有列，CREATE 新表（保留所有列 + 改 nullable + 加新列） + 复制数据 + 删老表。
沿用 2026_07_27_0003 的「反射 + 重建表」模式。

注意：上一条迁移 0003 留下过 activities_old 表（如果当时异常退出）。本迁移先探测并清掉。
"""
import json
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_07_28_0002"
down_revision = "2026_07_28_0001"
branch_labels = None
depends_on = None


def _col_info_to_ddl(name: str, col_type, nullable: bool, default, server_default, primary_key: bool) -> str:
    """把 inspect 拿到的列信息转成 SQLite CREATE TABLE 用的 DDL 片段。"""
    type_str = ""
    if isinstance(col_type, sa.JSON):
        type_str = "JSON"
    elif hasattr(col_type, "length") and col_type.length:
        type_str = f"VARCHAR({col_type.length})"
    elif isinstance(col_type, sa.Text):
        type_str = "TEXT"
    elif isinstance(col_type, sa.Boolean):
        type_str = "BOOLEAN"
    elif isinstance(col_type, (sa.Integer, sa.BigInteger)):
        type_str = "INTEGER"
    elif isinstance(col_type, sa.DateTime):
        type_str = "DATETIME"
    elif isinstance(col_type, sa.Numeric):
        type_str = f"NUMERIC({col_type.precision}, {col_type.scale})"
    else:
        type_str = "TEXT"

    parts = [name, type_str]
    if primary_key:
        parts.append("NOT NULL PRIMARY KEY AUTOINCREMENT")
    else:
        if not nullable:
            parts.append("NOT NULL")
    if server_default is not None and not primary_key:
        sd = server_default
        if hasattr(sd, "arg"):
            sd = sd.arg
        if hasattr(sd, "value"):
            sd = sd.value
        if isinstance(sd, str):
            sd_clean = sd.strip("'\"")
            parts.append(f"DEFAULT {sd_clean}")
    elif default is not None and not primary_key:
        parts.append(f"DEFAULT {default}")
    return " ".join(parts)


def upgrade() -> None:
    bind = op.get_bind()

    # 0) 兜底：清理上条迁移残留的 activities_old（异常退出时可能留下）
    bind.execute(sa.text("DROP TABLE IF EXISTS activities_old"))

    # 1) 反射当前 activities 表结构
    insp = sa.inspect(bind)
    cur_cols = insp.get_columns("activities")
    cur_fks = insp.get_foreign_keys("activities")
    cur_indexes = insp.get_indexes("activities")

    # 2) 构建新表 DDL：保留所有列，organizer_branch_id / source_type 改 nullable
    new_cols_ddl = []
    for c in cur_cols:
        cname = c["name"]
        ctype = c["type"]
        cnullable = c.get("nullable", True)
        cdefault = c.get("default", None)
        cserver_default = c.get("server_default", None)
        cprimary = bool(c.get("primary_key", False))

        if cname == "organizer_branch_id":
            # 改 nullable（保留字段做审计）
            cnullable = True
        elif cname == "source_type":
            # 改 nullable（被 organize_type 替代）
            cnullable = True
        new_cols_ddl.append(
            _col_info_to_ddl(cname, ctype, cnullable, cdefault, cserver_default, cprimary)
        )

    # 加新列：organize_type + co_organize_branch_ids
    col_names_in_ddl = [c.split()[0] for c in new_cols_ddl]
    if "organize_type" not in col_names_in_ddl:
        new_cols_ddl.append("organize_type VARCHAR(16) NOT NULL DEFAULT 'self_organize'")
    if "co_organize_branch_ids" not in col_names_in_ddl:
        new_cols_ddl.append("co_organize_branch_ids JSON NOT NULL DEFAULT '[]'")

    # 3) 外键
    fk_ddl = []
    for fk in cur_fks:
        ref_table = fk["referred_table"]
        ref_cols = ", ".join(fk["referred_columns"])
        local_cols = ", ".join(fk["constrained_columns"])
        fk_ddl.append(f"FOREIGN KEY({local_cols}) REFERENCES {ref_table}({ref_cols})")
    fk_ddl_str = ", ".join(fk_ddl)

    all_ddl_parts = new_cols_ddl + ([fk_ddl_str] if fk_ddl_str else [])
    create_sql = f"CREATE TABLE activities_new ({', '.join(all_ddl_parts)})"
    print(f"[activity_organize_v3] create new table SQL length: {len(create_sql)}")

    # 4) 重建表
    bind.execute(sa.text("ALTER TABLE activities RENAME TO activities_old"))
    bind.execute(sa.text(create_sql))

    # 5) 复制数据 + 业务迁移
    # 源列：原 activities 表所有列（包含 organizer_branch_id / source_type）
    src_cols = [c["name"] for c in cur_cols]
    src_cols_sql = ", ".join(src_cols)
    # 目标列：原列 + 新增的 organize_type / co_organize_branch_ids
    dst_cols = src_cols + [c for c in ["organize_type", "co_organize_branch_ids"] if c not in src_cols]
    dst_cols_sql = ", ".join(dst_cols)

    rows = bind.execute(sa.text(f"SELECT {src_cols_sql} FROM activities_old")).fetchall()
    print(f"[activity_organize_v3] migrating {len(rows)} activities rows")
    migrated = 0
    for row in rows:
        d = dict(zip(src_cols, row))
        # organize_type 默认 self_organize
        old_src = (d.get("source_type") or "self_organize")
        d["organize_type"] = old_src
        # co_organize_branch_ids：老 self_organize 的 organizer_branch_id 装进去
        if old_src == "self_organize" and d.get("organizer_branch_id"):
            d["co_organize_branch_ids"] = json.dumps([int(d["organizer_branch_id"])], ensure_ascii=False)
        else:
            d["co_organize_branch_ids"] = "[]"

        placeholders = ", ".join([f":{c}" for c in dst_cols])
        bind.execute(
            sa.text(f"INSERT INTO activities_new ({dst_cols_sql}) VALUES ({placeholders})"),
            d,
        )
        migrated += 1
    print(f"[activity_organize_v3] migrated {migrated} rows")

    # 6) 删老表
    bind.execute(sa.text("DROP TABLE activities_old"))
    bind.execute(sa.text("ALTER TABLE activities_new RENAME TO activities"))

    # 7) 重建索引：跳过 organizer_branch_id 的索引（不再用），其他全恢复
    skip_index_names = set()
    for idx in cur_indexes:
        cols_list = idx.get("column_names") or []
        if "organizer_branch_id" in cols_list:
            skip_index_names.add(idx["name"])
    for idx in cur_indexes:
        if idx["name"] in skip_index_names:
            print(f"[activity_organize_v3] skip recreating index {idx['name']} on organizer_branch_id")
            continue
        cols = ", ".join(idx["column_names"])
        name = idx["name"]
        unique = "UNIQUE " if idx.get("unique") else ""
        try:
            bind.execute(sa.text(f"CREATE {unique}INDEX IF NOT EXISTS {name} ON activities ({cols})"))
        except Exception as e:
            print(f"  [warn] could not recreate index {name}: {e}")

    # 8) 验证
    final_cols = [c["name"] for c in sa.inspect(bind).get_columns("activities")]
    print(f"[activity_organize_v3] final cols: {final_cols}")


def downgrade() -> None:
    bind = op.get_bind()
    # 反向：删除 organize_type / co_organize_branch_ids
    # 恢复 organizer_branch_id / source_type 为 NOT NULL
    # 数据层面：co_organize_branch_ids 第一个元素填回 organizer_branch_id
    bind.execute(sa.text("DROP TABLE IF EXISTS activities_old"))

    insp = sa.inspect(bind)
    cur_cols = insp.get_columns("activities")
    cur_fks = insp.get_foreign_keys("activities")
    cur_indexes = insp.get_indexes("activities")

    new_cols_ddl = []
    drop_cols = ["organize_type", "co_organize_branch_ids"]
    for c in cur_cols:
        cname = c["name"]
        if cname in drop_cols:
            continue
        ctype = c["type"]
        cnullable = c.get("nullable", True)
        cdefault = c.get("default", None)
        cserver_default = c.get("server_default", None)
        cprimary = bool(c.get("primary_key", False))
        # 恢复 NOT NULL
        if cname == "organizer_branch_id":
            cnullable = False
        if cname == "source_type":
            cnullable = False
        new_cols_ddl.append(
            _col_info_to_ddl(cname, ctype, cnullable, cdefault, cserver_default, cprimary)
        )

    fk_ddl = []
    for fk in cur_fks:
        ref_table = fk["referred_table"]
        ref_cols = ", ".join(fk["referred_columns"])
        local_cols = ", ".join(fk["constrained_columns"])
        fk_ddl.append(f"FOREIGN KEY({local_cols}) REFERENCES {ref_table}({ref_cols})")
    fk_ddl_str = ", ".join(fk_ddl)

    all_ddl_parts = new_cols_ddl + ([fk_ddl_str] if fk_ddl_str else [])
    create_sql = f"CREATE TABLE activities_old ({', '.join(all_ddl_parts)})"

    bind.execute(sa.text("ALTER TABLE activities RENAME TO activities_v3"))
    bind.execute(sa.text(create_sql))

    src_cols = [c["name"] for c in cur_cols if c["name"] not in drop_cols]
    src_cols_sql = ", ".join(src_cols)
    dst_cols = src_cols
    dst_cols_sql = ", ".join(dst_cols)

    rows = bind.execute(sa.text(f"SELECT {src_cols_sql} FROM activities_v3")).fetchall()
    for row in rows:
        d = dict(zip(src_cols, row))
        # 数据迁移反向：
        raw = d.get("co_organize_branch_ids", "[]")
        try:
            arr = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            arr = []
        # organizer_branch_id 取 co_organize_branch_ids 第一项
        if d.get("organizer_branch_id") is None and arr:
            d["organizer_branch_id"] = int(arr[0])
        # source_type 用 organize_type 还原
        if d.get("source_type") is None:
            d["source_type"] = d.get("organize_type", "self_organize")
        placeholders = ", ".join([f":{c}" for c in dst_cols])
        bind.execute(
            sa.text(f"INSERT INTO activities_old ({dst_cols_sql}) VALUES ({placeholders})"),
            d,
        )

    bind.execute(sa.text("DROP TABLE activities_v3"))
    bind.execute(sa.text("ALTER TABLE activities_old RENAME TO activities"))

    # 重建索引
    for idx in cur_indexes:
        cols = ", ".join(idx["column_names"])
        name = idx["name"]
        unique = "UNIQUE " if idx.get("unique") else ""
        try:
            bind.execute(sa.text(f"CREATE {unique}INDEX IF NOT EXISTS {name} ON activities ({cols})"))
        except Exception as e:
            print(f"  [warn] could not recreate index {name}: {e}")

    final_cols = [c["name"] for c in sa.inspect(bind).get_columns("activities")]
    print(f"[activity_organize_v3 downgrade] final cols: {final_cols}")
