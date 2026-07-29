"""修 activity_participants.activity_id 外键引用错误（指向 activities_old）

Revision ID: 2026_07_28_0003
Revises: 2026_07_28_0002
Create Date: 2026-07-28 10:35:00.000000

问题背景：
- 2026_07_27_0003_activity_v2_fields 迁移把 activities 重建为 activities_new，复制完数据后 drop activities_old。
- 但 activity_participants.activity_id 的 FOREIGN KEY 仍然指向 "activities_old"(id)。
- 在线上的数据库，SQLite 真的把"activities_old"作为外键引用存下来了。
- 这导致：插入 activity_participants 时报 "no such table: main.activities_old"。

修法：重建 activity_participants 表，FK 指向正确的 "activities" 表。

策略：CREATE new table + 复制数据 + drop old + rename（同 v2 重建模式）。
"""
from alembic import op
import sqlalchemy as sa


revision = "2026_07_28_0003"
down_revision = "2026_07_28_0002"
branch_labels = None
depends_on = None


def _col_info_to_ddl(name, col_type, nullable, default, server_default, primary_key):
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
    bind.execute(sa.text("DROP TABLE IF EXISTS activity_participants_old"))

    insp = sa.inspect(bind)
    cur_cols = insp.get_columns("activity_participants")
    cur_indexes = insp.get_indexes("activity_participants")
    cur_uniques = insp.get_unique_constraints("activity_participants")

    # 反射出旧的 FK 列表，丢弃所有 FK（重建时只保留指向正确 activities 表的 FK）
    new_cols_ddl = []
    for c in cur_cols:
        new_cols_ddl.append(
            _col_info_to_ddl(
                c["name"], c["type"], c.get("nullable", True),
                c.get("default", None), c.get("server_default", None),
                bool(c.get("primary_key", False)),
            )
        )
    # 加 UNIQUE 约束
    for uq in cur_uniques:
        cols = ", ".join(uq["column_names"])
        new_cols_ddl.append(f"UNIQUE({cols})")

    # 关键：FK 指向正确的 "activities"（不是 "activities_old"）
    fk_ddl_str = (
        "FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE, "
        "FOREIGN KEY(member_id) REFERENCES members(id)"
    )

    all_ddl_parts = new_cols_ddl + [fk_ddl_str]
    create_sql = f"CREATE TABLE activity_participants_new ({', '.join(all_ddl_parts)})"
    print(f"[fix_ap_fk] create SQL length: {len(create_sql)}")

    bind.execute(sa.text("ALTER TABLE activity_participants RENAME TO activity_participants_old"))
    bind.execute(sa.text(create_sql))

    # 复制数据
    src_cols = [c["name"] for c in cur_cols]
    src_cols_sql = ", ".join(src_cols)
    dst_cols = src_cols
    dst_cols_sql = ", ".join(dst_cols)
    rows = bind.execute(sa.text(f"SELECT {src_cols_sql} FROM activity_participants_old")).fetchall()
    print(f"[fix_ap_fk] migrating {len(rows)} activity_participants rows")
    placeholders = ", ".join([f":{c}" for c in dst_cols])
    for row in rows:
        d = dict(zip(src_cols, row))
        bind.execute(
            sa.text(f"INSERT INTO activity_participants_new ({dst_cols_sql}) VALUES ({placeholders})"),
            d,
        )

    bind.execute(sa.text("DROP TABLE activity_participants_old"))
    bind.execute(sa.text("ALTER TABLE activity_participants_new RENAME TO activity_participants"))

    # 重建索引
    for idx in cur_indexes:
        cols = ", ".join(idx["column_names"])
        name = idx["name"]
        unique = "UNIQUE " if idx.get("unique") else ""
        try:
            bind.execute(sa.text(f"CREATE {unique}INDEX IF NOT EXISTS {name} ON activity_participants ({cols})"))
        except Exception as e:
            print(f"  [warn] could not recreate index {name}: {e}")

    print(f"[fix_ap_fk] migration done")


def downgrade() -> None:
    # 不做反向：回到 broken 状态没意义
    pass
