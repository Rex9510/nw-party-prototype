"""normalize members.identities labels

Revision ID: 2026_07_27_0002
Revises: 2026_07_27_0001
Create Date: 2026-07-27 19:30:00.000000

迁移规则（identities 是 JSON 字符串，存中文 label）:
  '党委委员'      -> '委员'
  '支委会委员'    -> '委员'
  '党委副书记'    -> '副书记'
  '党支部书记'    -> '书记'
  '普通党员'      -> 保持
  其他/未知值     -> 保持

实现：Python 走 SQLAlchemy，JSON 解析 + set 重写 + 写回。
SQLite 没有原生 JSON 操作函数支持 list 元素替换，Python 处理最稳。

"""
import json
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_07_27_0002"
down_revision = "2026_07_27_0001"
branch_labels = None
depends_on = None


# 映射表：旧 label -> 新 label
IDENTITY_RENAMES = {
    "党委委员": "委员",
    "支委会委员": "委员",
    "党委副书记": "副书记",
    "党支部书记": "书记",
    # "普通党员" 保持原样
}


def upgrade() -> None:
    bind = op.get_bind()
    # 1) 拉所有非空 identities 行
    rows = bind.execute(
        sa.text("SELECT id, identities FROM members WHERE identities IS NOT NULL AND identities != '' AND identities != '[]'")
    ).fetchall()
    print(f"[normalize_identities] {len(rows)} members with identities to scan")

    updated = 0
    touched_ids = []
    for row in rows:
        mid = row[0]
        raw = row[1]
        if not raw:
            continue
        try:
            arr = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            print(f"  [skip] id={mid} bad JSON: {raw!r}")
            continue
        if not isinstance(arr, list):
            print(f"  [skip] id={mid} not a list: {raw!r}")
            continue

        new_arr = []
        changed = False
        for item in arr:
            if not isinstance(item, str):
                new_arr.append(item)
                continue
            if item in IDENTITY_RENAMES:
                new_item = IDENTITY_RENAMES[item]
                if new_item != item:
                    changed = True
                new_arr.append(new_item)
            else:
                new_arr.append(item)

        if changed:
            new_json = json.dumps(new_arr, ensure_ascii=False)
            bind.execute(
                sa.text("UPDATE members SET identities = :v WHERE id = :id"),
                {"v": new_json, "id": mid},
            )
            updated += 1
            touched_ids.append(mid)
            print(f"  [updated] id={mid} {raw} -> {new_json}")

    print(f"[normalize_identities] done: {updated} members updated, touched_ids={touched_ids}")


def downgrade() -> None:
    # 反向迁移：新 -> 旧（如果出现冲突会保留原值，跳过）
    REVERSE_RENAMES = {v: k for k, v in IDENTITY_RENAMES.items()}
    # 注意：'副书记' 反向到 '党委副书记'；'书记' 反向到 '党支部书记'；
    # '委员' 反向到 '党委委员'（有歧义但只能选一个，按降序保留）
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, identities FROM members WHERE identities IS NOT NULL AND identities != '' AND identities != '[]'")
    ).fetchall()

    for row in rows:
        mid = row[0]
        raw = row[1]
        if not raw:
            continue
        try:
            arr = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(arr, list):
            continue

        new_arr = []
        changed = False
        for item in arr:
            if not isinstance(item, str):
                new_arr.append(item)
                continue
            if item in REVERSE_RENAMES:
                new_arr.append(REVERSE_RENAMES[item])
                changed = True
            else:
                new_arr.append(item)

        if changed:
            new_json = json.dumps(new_arr, ensure_ascii=False)
            bind.execute(
                sa.text("UPDATE members SET identities = :v WHERE id = :id"),
                {"v": new_json, "id": mid},
            )
            print(f"  [downgrade] id={mid} -> {new_json}")
