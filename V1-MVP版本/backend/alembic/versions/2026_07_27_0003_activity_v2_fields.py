"""v2: activities 加 upper_org + study_methods + audience_category 改 JSON 多选

Revision ID: 2026_07_27_0003
Revises: 2026_07_27_0002
Create Date: 2026-07-27 19:50:00.000000

改动：
1. activities.upper_org        新增（String(50)，nullable）
2. activities.study_methods    新增（JSON，default='[]'，not null）
3. activities.audience_category
   - 老 String(16) → JSON
   - 迁移：老 'foo' → ['foo']（单元素数组）

数据迁移用 Python（SQLite 没有原生 JSON list 操作，str 字段 → JSON 字段要 ALTER COLUMN 重建）。

策略：动态探测 activities 表的所有列，原样 CREATE 新表（保留所有旧列） + 复制数据。
这样不管 lecturer_bio 在不在、所有列都保留。

"""
import json
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_07_27_0003"
down_revision = "2026_07_27_0002"
branch_labels = None
depends_on = None


def _col_info_to_ddl(name: str, col_type, nullable: bool, default, server_default, primary_key: bool) -> str:
    """把 inspect 拿到的列信息转成 SQLite CREATE TABLE 用的 DDL 片段。"""
    # 简单类型映射（够用：VARCHAR/TEXT/INTEGER/BIGINT/BOOLEAN/DATETIME/NUMERIC/JSON）
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
    # server_default 优先
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

    # 1) 加 upper_org (String 50, nullable)
    with op.batch_alter_table("activities") as batch:
        batch.add_column(sa.Column("upper_org", sa.String(length=50), nullable=True))

    # 2) 加 study_methods (JSON, default '[]', not null)
    with op.batch_alter_table("activities") as batch:
        batch.add_column(
            sa.Column(
                "study_methods",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )

    # 3) audience_category: String(16) → JSON
    # SQLite 3.35+ 支持 DROP COLUMN，但生产可能更老；用 复制 + 重建 + 改名 最稳
    # 反射当前 activities 表的所有列 + 主键 + 外键
    insp = sa.inspect(bind)
    cur_cols = insp.get_columns("activities")
    cur_pk = insp.get_pk_constraint("activities")
    cur_fks = insp.get_foreign_keys("activities")
    cur_indexes = insp.get_indexes("activities")

    # 构建新表 DDL（保留所有列，把 audience_category 类型改成 JSON）
    new_cols_ddl = []
    for c in cur_cols:
        if c["name"] == "audience_category":
            # 替换为 JSON + server_default='[]'
            new_cols_ddl.append(
                "audience_category JSON NOT NULL DEFAULT '[]'"
            )
        else:
            new_cols_ddl.append(
                _col_info_to_ddl(
                    c["name"],
                    c["type"],
                    c.get("nullable", True),
                    c.get("default", None),
                    c.get("server_default", None),
                    bool(c.get("primary_key", False)),
                )
            )
    # 加 study_methods / upper_org（已经在 1, 2 步加了，反射应该看到了）
    col_names_in_ddl = [c.split()[0] for c in new_cols_ddl]
    if "upper_org" not in col_names_in_ddl:
        new_cols_ddl.append("upper_org VARCHAR(50)")
    if "study_methods" not in col_names_in_ddl:
        new_cols_ddl.append("study_methods JSON NOT NULL DEFAULT '[]'")

    # 外键
    fk_ddl = []
    for fk in cur_fks:
        ref_table = fk["referred_table"]
        ref_cols = ", ".join(fk["referred_columns"])
        local_cols = ", ".join(fk["constrained_columns"])
        fk_ddl.append(f"FOREIGN KEY({local_cols}) REFERENCES {ref_table}({ref_cols})")
    fk_ddl_str = ", ".join(fk_ddl)

    # 注意：PK 已在 _col_info_to_ddl 中 inline 输出（列级 PRIMARY KEY），
    # 不可再追加表级 PRIMARY KEY，否则 SQLite 报 "more than one primary key"。
    # 所以只拼接 列DDL + 外键。
    all_ddl_parts = new_cols_ddl + ([fk_ddl_str] if fk_ddl_str else [])
    create_sql = f"CREATE TABLE activities_new ({', '.join(all_ddl_parts)})"
    print(f"[activity_v2_fields] create new table SQL length: {len(create_sql)}")
    bind.execute(sa.text("ALTER TABLE activities RENAME TO activities_old"))
    bind.execute(sa.text(create_sql))

    # 复制数据
    # SELECT 必须包含 audience_category（从老表读取旧值）
    src_cols = [c["name"] for c in cur_cols]  # ALL columns including audience_category
    src_cols_sql = ", ".join(src_cols)
    # INSERT 目标列：老列名全部保留，audience_category 指向新 JSON 列（同名）
    dst_cols = src_cols
    dst_cols_sql = ", ".join(dst_cols)

    rows = bind.execute(sa.text(f"SELECT {src_cols_sql} FROM activities_old")).fetchall()
    print(f"[activity_v2_fields] migrating {len(rows)} activities rows")
    migrated = 0
    for row in rows:
        d = dict(zip(src_cols, row))
        old_aud = d.get("audience_category")
        if old_aud is None or old_aud == "":
            new_aud = "[]"
        else:
            new_aud = json.dumps([old_aud], ensure_ascii=False)
        d["audience_category"] = new_aud
        # 占位 upper_org
        if d.get("source_type") == "upper_send" and not d.get("upper_org"):
            d["upper_org"] = "（待补充）"
        # 写：INSERT INTO activities_new (cols) VALUES (?, ?, ...)
        placeholders = ", ".join([f":{c}" for c in dst_cols])
        bind.execute(
            sa.text(f"INSERT INTO activities_new ({dst_cols_sql}) VALUES ({placeholders})"),
            d,
        )
        migrated += 1
    print(f"[activity_v2_fields] migrated {migrated} rows")

    # 删老表
    bind.execute(sa.text("DROP TABLE activities_old"))
    bind.execute(sa.text("ALTER TABLE activities_new RENAME TO activities"))

    # 重建索引
    for idx in cur_indexes:
        cols = ", ".join(idx["column_names"])
        name = idx["name"]
        unique = "UNIQUE " if idx.get("unique") else ""
        try:
            bind.execute(sa.text(f"CREATE {unique}INDEX IF NOT EXISTS {name} ON activities ({cols})"))
        except Exception as e:
            print(f"  [warn] could not recreate index {name}: {e}")

    # 验证
    final_cols = [c["name"] for c in sa.inspect(bind).get_columns("activities")]
    print(f"[activity_v2_fields] final cols: {final_cols}")


def downgrade() -> None:
    bind = op.get_bind()

    # 1) audience_category: JSON → String(16)（取数组第一个）
    insp = sa.inspect(bind)
    cur_cols = insp.get_columns("activities")

    # 跟 upgrade 一样的反射 + CREATE NEW 模式
    new_cols_ddl = []
    for c in cur_cols:
        if c["name"] == "audience_category":
            new_cols_ddl.append("audience_category VARCHAR(16)")
        else:
            new_cols_ddl.append(
                _col_info_to_ddl(
                    c["name"],
                    c["type"],
                    c.get("nullable", True),
                    c.get("default", None),
                    c.get("server_default", None),
                    bool(c.get("primary_key", False)),
                )
            )

    # 不需要 upper_org / study_methods 了
    drop_cols = ["upper_org", "study_methods"]
    new_cols_ddl = [d for d in new_cols_ddl if d.split()[0] not in drop_cols]

    fks = insp.get_foreign_keys("activities")
    fk_ddl = []
    for fk in fks:
        ref_table = fk["referred_table"]
        ref_cols = ", ".join(fk["referred_columns"])
        local_cols = ", ".join(fk["constrained_columns"])
        fk_ddl.append(f"FOREIGN KEY({local_cols}) REFERENCES {ref_table}({ref_cols})")
    fk_ddl_str = ", ".join(fk_ddl)

    all_ddl_parts = new_cols_ddl + ([fk_ddl_str] if fk_ddl_str else [])
    create_sql = f"CREATE TABLE activities_old ({', '.join(all_ddl_parts)})"

    bind.execute(sa.text("ALTER TABLE activities RENAME TO activities_v2"))
    bind.execute(sa.text(create_sql))

    src_cols = [c["name"] for c in cur_cols if c["name"] not in drop_cols]
    # audience_category 也在 SELECT 中（从 JSON 列读取值再转回 VARCHAR）
    src_cols_sql = ", ".join(src_cols)
    dst_cols = src_cols  # 列名一致，不需要 +audience_category
    dst_cols_sql = ", ".join(dst_cols)

    rows = bind.execute(sa.text(f"SELECT {src_cols_sql} FROM activities_v2")).fetchall()
    for row in rows:
        d = dict(zip(src_cols, row))
        # audience_category 还原
        raw = d.get("audience_category", "[]")
        try:
            arr = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            arr = []
        first = (arr[0] if arr else "") or ""
        d["audience_category"] = first[:16]
        placeholders = ", ".join([f":{c}" for c in dst_cols])
        bind.execute(
            sa.text(f"INSERT INTO activities_old ({dst_cols_sql}) VALUES ({placeholders})"),
            d,
        )

    bind.execute(sa.text("DROP TABLE activities_v2"))
    bind.execute(sa.text("ALTER TABLE activities_old RENAME TO activities"))

    final_cols = [c["name"] for c in sa.inspect(bind).get_columns("activities")]
    print(f"[activity_v2_fields downgrade] final cols: {final_cols}")
