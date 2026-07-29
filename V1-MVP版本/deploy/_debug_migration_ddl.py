"""模拟迁移脚本的 DDL 生成，打印出实际要执行的 CREATE TABLE SQL。"""
import json
import sqlite3
import sqlalchemy as sa

DB = r'E:\new party\nw-party-prototype\V1-MVP版本\nwparty_prod_fresh.db'

engine = sa.create_engine(f'sqlite:///{DB}')
with engine.connect() as conn:
    insp = sa.inspect(engine)
    
    # 1) 先看当前 activities 表的列
    cur_cols = insp.get_columns("activities")
    cur_pk = insp.get_pk_constraint("activities")
    cur_fks = insp.get_foreign_keys("activities")
    cur_indexes = insp.get_indexes("activities")
    
    print("=== current columns ===")
    for c in cur_cols:
        print(f"  {c['name']:25s} type={c['type']!r:40s} nullable={c.get('nullable')} default={c.get('default')!r} server_default={c.get('server_default')!r} pk={c.get('primary_key')}")
    
    print(f"\n=== PK ===")
    print(f"  {cur_pk}")
    print(f"\n=== FKs ===")
    for fk in cur_fks:
        print(f"  {fk}")
    print(f"\n=== indexes ===")
    for idx in cur_indexes:
        print(f"  {idx}")

    # 2) 模拟 step 1 & 2 加列后的效果
    # 模拟 reflect 已经加了列之后的表
    # 直接模拟 _col_info_to_ddl 对每个列的处理
    
    def col_info_to_ddl(name, col_type, nullable, default, server_default, primary_key):
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
            type_str = f"??{type(col_type).__name__}??"
        
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

    new_cols_ddl = []
    for c in cur_cols:
        if c["name"] == "audience_category":
            new_cols_ddl.append("audience_category_new JSON NOT NULL DEFAULT '[]'")
        else:
            new_cols_ddl.append(
                col_info_to_ddl(
                    c["name"], c["type"],
                    c.get("nullable", True),
                    c.get("default", None),
                    c.get("server_default", None),
                    bool(c.get("primary_key", False)),
                )
            )
    
    # 加上 study_methods / upper_org
    col_names_in_ddl = [c.split()[0] for c in new_cols_ddl]
    if "upper_org" not in col_names_in_ddl:
        new_cols_ddl.append("upper_org VARCHAR(50)")
    if "study_methods" not in col_names_in_ddl:
        new_cols_ddl.append("study_methods JSON NOT NULL DEFAULT '[]'")
    
    pk_cols = cur_pk.get("constrained_columns", ["id"])
    pk_ddl = f"PRIMARY KEY ({', '.join(pk_cols)} AUTOINCREMENT)" if pk_cols else ""
    
    fk_ddl = []
    for fk in cur_fks:
        ref_table = fk["referred_table"]
        ref_cols = ", ".join(fk["referred_columns"])
        local_cols = ", ".join(fk["constrained_columns"])
        fk_ddl.append(f"FOREIGN KEY({local_cols}) REFERENCES {ref_table}({ref_cols})")
    fk_ddl_str = ", ".join(fk_ddl)
    
    all_ddl_parts = new_cols_ddl + ([pk_ddl] if pk_ddl else []) + ([fk_ddl_str] if fk_ddl_str else [])
    create_sql = f"CREATE TABLE activities_new ({', '.join(all_ddl_parts)})"
    
    print(f"\n=== Generated CREATE TABLE DDL ({len(create_sql)} chars) ===")
    print(create_sql)
    
    # 3) 实际测试执行
    print("\n=== Test executing DDL ===")
    try:
        conn.execute(sa.text(create_sql))
        print("  OK: CREATE TABLE succeeded")
        conn.execute(sa.text("DROP TABLE activities_new"))
        print("  OK: DROP TABLE succeeded")
    except Exception as e:
        print(f"  FAIL: {e}")
