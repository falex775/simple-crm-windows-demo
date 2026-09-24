"""Generate a small FastAPI + SQLite application from a simple application spec.

Example spec:

    - Customer
    - Product
    - Customer Product Relationship

    1. Customer
       - id: integer
       - name: string
       - email: string
       - phone: string

    2. Product
       - id: integer
       - name: string

    3. Customer Product Relationship
       - customer_id: integer
       - product_id: integer
       - uniqueness constraint: one pair only

The generator writes a self-contained FastAPI prototype using SQLite. It supports
multiple CRUD entities and one relationship entity.
"""

from __future__ import annotations

import argparse
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path


ENTITY_HEADER_RE = re.compile(r"^\s*\d+\.\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^\s*-\s*([A-Za-z_][A-Za-z0-9_\s]*)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")
ENDPOINT_RE = re.compile(r"^\s*(?:GET|POST|PUT|DELETE)\s+/api/([A-Za-z0-9_\-]+)(?:\?.*)?(?:/\{[^}]+\})?\s*$", re.I)


@dataclass
class FieldSpec:
    name: str
    type_name: str
    is_id: bool = False

    @property
    def python_type(self) -> str:
        mapping = {
            "int": "int",
            "integer": "int",
            "float": "float",
            "number": "float",
            "decimal": "float",
            "bool": "bool",
            "boolean": "bool",
            "str": "str",
            "string": "str",
            "text": "str",
            "date": "str",
            "datetime": "str",
        }
        return mapping.get(self.type_name.lower(), "str")

    @property
    def sqlite_type(self) -> str:
        mapping = {
            "int": "INTEGER",
            "integer": "INTEGER",
            "float": "REAL",
            "number": "REAL",
            "decimal": "REAL",
            "bool": "INTEGER",
            "boolean": "INTEGER",
            "str": "TEXT",
            "string": "TEXT",
            "text": "TEXT",
            "date": "TEXT",
            "datetime": "TEXT",
        }
        return mapping.get(self.type_name.lower(), "TEXT")


@dataclass
class EntitySpec:
    name: str
    fields: list[FieldSpec] = field(default_factory=list)
    route: str = ""
    is_relationship: bool = False

    @property
    def class_name(self) -> str:
        return "".join(part.capitalize() for part in self.name.split())

    @property
    def table_name(self) -> str:
        return self.route or snake_case(self.name)


def snake_case(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", " ", value).strip().lower()
    return re.sub(r"\s+", "_", value)


def pluralize(value: str) -> str:
    value = snake_case(value)
    if value.endswith("y") and not value.endswith(("ay", "ey", "iy", "oy", "uy")):
        return value[:-1] + "ies"
    if value.endswith("s"):
        return value
    return value + "s"


def normalize_entity_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9\s_-]", " ", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def normalize_field_name(value: str) -> str:
    value = value.strip().lower().replace("-", "_")
    value = re.sub(r"[^a-z0-9_\s]", " ", value)
    value = re.sub(r"\s+", "_", value)
    return value.strip("_")


def parse_spec(text: str) -> list[EntitySpec]:
    lines = text.splitlines()
    entries: list[EntitySpec] = []
    route_overrides: dict[str, str] = {}

    for raw_line in lines:
        line = raw_line.strip()
        match = ENDPOINT_RE.match(line)
        if match:
            route_overrides[match.group(1)] = match.group(1)

    active_title = None
    active_fields: list[FieldSpec] = []

    def flush() -> None:
        nonlocal active_title, active_fields
        if not active_title:
            return
        entity_name = normalize_entity_name(active_title)
        if not entity_name:
            return
        fields = list(active_fields)
        if not fields:
            raise ValueError(f"Entity '{entity_name}' does not contain any fields")

        inferred_route = route_overrides.get(pluralize(entity_name), pluralize(entity_name))
        inferred_route = inferred_route.lower()
        is_relationship = (
            "relationship" in entity_name.lower()
            or any(field.name.endswith("_id") for field in fields)
            and len([field for field in fields if field.name.endswith("_id")]) >= 2
        )

        if not any(field.name == "id" for field in fields):
            fields.insert(0, FieldSpec(name="id", type_name="integer", is_id=True))
        entries.append(
            EntitySpec(
                name=entity_name,
                fields=fields,
                route=inferred_route,
                is_relationship=is_relationship,
            )
        )
        active_title = None
        active_fields = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        header = ENTITY_HEADER_RE.match(line)
        if header:
            flush()
            active_title = header.group(1).strip()
            continue

        if active_title is None:
            continue

        field_match = FIELD_RE.match(line)
        if field_match:
            field_name = normalize_field_name(field_match.group(1))
            field_type = field_match.group(2).strip()
            is_id = field_name == "id"
            field = FieldSpec(name=field_name, type_name=field_type, is_id=is_id)
            active_fields.append(field)

    flush()

    if not entries:
        raise ValueError("No entities were found. Use numbered sections like '1. Customer'.")

    relationship_entities = [entity for entity in entries if entity.is_relationship]
    if len(relationship_entities) > 1:
        raise ValueError("This generator currently supports only one relationship entity.")

    return entries


def render_model(entity: EntitySpec) -> str:
    fields = [field for field in entity.fields if not field.is_id]
    model_lines = [f"class {entity.class_name}(BaseModel):"]
    if not fields:
        model_lines.append("    pass")
    else:
        for field in fields:
            model_lines.append(f"    {field.name}: {field.python_type}")

    if entity.is_relationship:
        model_lines.append("")
        model_lines.append(f"class {entity.class_name}Read({entity.class_name}):")
        model_lines.append("    pass")
    return "\n".join(model_lines) + "\n"


def render_entity_create_model(entity: EntitySpec) -> str:
    lines = [f"class {entity.class_name}Create(BaseModel):"]
    for field in [f for f in entity.fields if not f.is_id]:
        lines.append(f"    {field.name}: {field.python_type} = Field(...)")
    lines.append("")
    lines.append(f"class {entity.class_name}Update(BaseModel):")
    for field in [f for f in entity.fields if not f.is_id]:
        lines.append(f"    {field.name}: {field.python_type} | None = None")
    lines.append("")
    lines.append(f"class {entity.class_name}Record({entity.class_name}Create):")
    lines.append("    id: int")
    return "\n".join(lines) + "\n"


def render_list_endpoint(entity: EntitySpec) -> str:
    fields = [f.name for f in entity.fields if not f.is_id]
    if not fields:
        return ""

    search_clauses = " OR ".join(f"LOWER(CAST({name} AS TEXT)) LIKE ?" for name in fields)
    params = ", ".join(f"'%{{search.lower()}}%'" for _ in fields)
    if fields:
        order_by = "name" if "name" in fields else fields[0]
    else:
        order_by = "id"

    return textwrap.dedent(
        f'''
        @app.get("/api/{entity.route}")
        def list_{entity.route}(search: str = ""):
            with db() as con:
                if search:
                    sql = "SELECT * FROM {entity.table_name} WHERE {search_clauses} ORDER BY {order_by}"
                    params = [{params}]
                    rows = con.execute(sql, params).fetchall()
                else:
                    rows = con.execute("SELECT * FROM {entity.table_name} ORDER BY {order_by}").fetchall()
            return [dict(row) for row in rows]

        @app.post("/api/{entity.route}")
        def create_{entity.route}(payload: {entity.class_name}Create):
            with db() as con:
                values = ({', '.join(f'payload.{name}' for name in fields)})
                cur = con.execute(
                    "INSERT INTO {entity.table_name}({', '.join(fields)}) VALUES({', '.join('?' for _ in fields)})",
                    values,
                )
                created_id = cur.lastrowid
            return {{"id": created_id, **payload.model_dump()}}

        @app.put("/api/{entity.route}/{{item_id}}")
        def update_{entity.route}(item_id: int, payload: {entity.class_name}Update):
            with db() as con:
                updates = payload.model_dump(exclude_unset=True)
                if not updates:
                    existing = con.execute("SELECT * FROM {entity.table_name} WHERE id = ?", (item_id,)).fetchone()
                    if existing is None:
                        raise HTTPException(404, "{entity.class_name} not found")
                    return dict(existing)

                assignment = ", ".join(f"{key} = ?" for key in updates)
                params = list(updates.values()) + [item_id]
                cur = con.execute(f"UPDATE {entity.table_name} SET {{assignment}} WHERE id = ?", params)
                if cur.rowcount == 0:
                    raise HTTPException(404, "{entity.class_name} not found")

                row = con.execute("SELECT * FROM {entity.table_name} WHERE id = ?", (item_id,)).fetchone()
                return dict(row)

        @app.delete("/api/{entity.route}/{{item_id}}")
        def delete_{entity.route}(item_id: int):
            with db() as con:
                cur = con.execute("DELETE FROM {entity.table_name} WHERE id = ?", (item_id,))
                if cur.rowcount == 0:
                    raise HTTPException(404, "{entity.class_name} not found")
            return {{"ok": True}}
        '''
    ).strip() + "\n\n"


def render_relationship_endpoint(entity: EntitySpec) -> str:
    table = entity.table_name
    fields = [f.name for f in entity.fields if not f.is_id]
    if not fields:
        return ""

    relation_lines = []
    for field_name in fields:
        target = field_name[:-3] if field_name.endswith("_id") else field_name
        relation_lines.append(
            f'''    if con.execute("SELECT 1 FROM {target}s WHERE id = ?", (payload.{field_name},)).fetchone() is None:\n        raise HTTPException(404, "{target.title()} not found")'''
        )

    return textwrap.dedent(
        f'''
        @app.post("/api/{entity.route}")
        def create_{entity.route}(payload: {entity.class_name}Create):
            with db() as con:
{chr(10).join(f"{line}" for line in relation_lines)}
                try:
                    con.execute(
                        "INSERT INTO {table}({', '.join(fields)}) VALUES({', '.join('?' for _ in fields)})",
                        ({', '.join(f'payload.{name}' for name in fields)}),
                    )
                except sqlite3.IntegrityError:
                    raise HTTPException(409, "This relationship already exists")
            return payload.model_dump()
        '''
    ).strip() + "\n\n"


def render_database_init(entities: list[EntitySpec]) -> str:
    table_statements = []
    for entity in entities:
        table_name = entity.table_name
        if entity.is_relationship:
            non_id_fields = [field for field in entity.fields if not field.is_id]
            columns = [f"{field.name} {field.sqlite_type} NOT NULL" for field in non_id_fields]
            columns_text = ",\n                ".join(columns)
            table_statements.append(
                f"CREATE TABLE IF NOT EXISTS {table_name}(\n                {columns_text},\n                PRIMARY KEY ({', '.join(field.name for field in non_id_fields)})\n            );"
            )
        else:
            non_id_fields = [field for field in entity.fields if not field.is_id]
            columns = ["id INTEGER PRIMARY KEY"]
            for field in non_id_fields:
                columns.append(f"{field.name} {field.sqlite_type} NOT NULL")
            columns_text = ",\n                ".join(columns)
            table_statements.append(f"CREATE TABLE IF NOT EXISTS {table_name}(\n                {columns_text}\n            );")

    return "\n            ".join(table_statements)


def generate_app(spec_text: str) -> str:
    entities = parse_spec(spec_text)

    model_blocks = []
    for entity in entities:
        if entity.is_relationship:
            model_blocks.append(render_entity_create_model(entity))
        else:
            model_blocks.append(render_entity_create_model(entity))

    endpoint_blocks = []
    for entity in entities:
        if entity.is_relationship:
            endpoint_blocks.append(render_relationship_endpoint(entity))
        else:
            endpoint_blocks.append(render_list_endpoint(entity))

    code = f'''from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB_PATH = Path(__file__).with_name("generated.db")


{chr(10).join(model_blocks)}

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with db() as con:
        con.executescript("""
            {render_database_init(entities)}
        """)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Generated Prototype", lifespan=lifespan)


@app.get("/")
def home():
    return {{"message": "Generated prototype", "docs": "/docs"}}


{''.join(endpoint_blocks)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("generated_main:app", host="127.0.0.1", port=8000, reload=True)
'''
    return code


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="Path to the application specification file.")
    parser.add_argument("-o", "--output", type=Path, default=Path("generated_main.py"), help="Output Python file path.")
    args = parser.parse_args()

    spec_text = args.spec.read_text(encoding="utf-8")
    generated = generate_app(spec_text)
    args.output.write_text(generated, encoding="utf-8")
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()


# The generated app will look roughly like this:
#   - a SQLite DB file named generated.db
#   - CRUD endpoints for each entity
#   - one relationship POST endpoint for the relationship entity
#   - validation and HTTP 404/409 errors for missing or duplicate links
#   - FastAPI docs served automatically at /docs
