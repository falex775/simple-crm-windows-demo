"""Generate a small FastAPI + SQLite prototype from an application spec.

Usage:
    python generate_app.py spec.md --output generated_main.py

The input is intentionally a lightweight Markdown-like document. Entity names,
field names, and types are read from the ``Core Entities`` section; endpoint
routes are read when present and otherwise inferred from the entity names.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


FIELD_RE = re.compile(r"^\s*-\s*([A-Za-z_][\w ]*)\s*:\s*([A-Za-z_][\w ]*)\s*$")
ENTITY_RE = re.compile(r"^\s*\d+\.\s+(.+?)\s*$")
ENDPOINT_RE = re.compile(r"^\s*-\s*(GET|POST|PUT|DELETE)\s+/api/([^/?]+)(?:\?[^ ]*)?(?:/\{[^}]+\})?\s*$", re.I)


@dataclass(frozen=True)
class Field:
    name: str
    type_name: str


@dataclass(frozen=True)
class Entity:
    name: str
    fields: tuple[Field, ...]
    route: str
    relationship: bool = False

    @property
    def class_name(self) -> str:
        return "".join(part.capitalize() for part in self.name.split())


@dataclass(frozen=True)
class Spec:
    entities: tuple[Entity, ...]
    relationship: Entity | None


def snake(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", " ", value).strip().lower()
    return re.sub(r"\s+", "_", value)


def plural(value: str) -> str:
    value = snake(value)
    if value.endswith("y") and not value.endswith(("ay", "ey", "iy", "oy", "uy")):
        return value[:-1] + "ies"
    if value.endswith("s"):
        return value
    return value + "s"


def parse_spec(text: str) -> Spec:
    """Parse the entity and endpoint portions of a specification."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current: tuple[str, list[str]] | None = None
    for line in lines:
        match = ENTITY_RE.match(line)
        if match:
            current = (match.group(1).strip(), [])
            sections.append(current)
        elif current is not None:
            current[1].append(line)

    if not sections:
        raise ValueError("No numbered entities were found in the Core Entities section")

    endpoint_routes: dict[str, str] = {}
    for line in lines:
        match = ENDPOINT_RE.match(line)
        if match:
            route = match.group(2).strip("/")
            endpoint_routes.setdefault(route, route)

    parsed: list[Entity] = []
    for title, body in sections:
        fields: list[Field] = []
        for line in body:
            match = FIELD_RE.match(line)
            if not match:
                continue
            name = snake(match.group(1))
            if name == "id" or "uniqueness constraint" in name:
                continue
            fields.append(Field(name, match.group(2).strip().lower()))

        if not fields:
            raise ValueError(f"Entity '{title}' has no fields")
        if any(not re.fullmatch(r"[a-z_][a-z0-9_]*", field.name) for field in fields):
            raise ValueError(f"Entity '{title}' contains an invalid field name")

        is_relationship = "relationship" in title.lower() or (
            len(fields) >= 2 and all(field.name.endswith("_id") for field in fields)
        )
        route = next((r for r in endpoint_routes if r == plural(title)), plural(title))
        parsed.append(Entity(title, tuple(fields), route, is_relationship))

    relationships = [entity for entity in parsed if entity.relationship]
    if len(relationships) > 1:
        raise ValueError("Only one relationship entity is supported by this prototype")
    relationship = relationships[0] if relationships else None
    entities = tuple(entity for entity in parsed if not entity.relationship)
    if not entities:
        raise ValueError("At least one non-relationship entity is required")
    return Spec(entities, relationship)


def sqlite_type(type_name: str) -> str:
    if type_name in {"integer", "int"}:
        return "INTEGER"
    if type_name in {"float", "number", "decimal"}:
        return "REAL"
    if type_name in {"boolean", "bool"}:
        return "INTEGER"
    return "TEXT"


def python_type(type_name: str) -> str:
    if type_name in {"integer", "int"}:
        return "int"
    if type_name in {"float", "number", "decimal"}:
        return "float"
    if type_name in {"boolean", "bool"}:
        return "bool"
    return "str"


def make_schema(spec: Spec) -> str:
    tables: list[str] = []
    for entity in (*spec.entities, *([spec.relationship] if spec.relationship else [])):
        columns = ["id INTEGER PRIMARY KEY"] if not entity.relationship else []
        columns.extend(f"{field.name} {sqlite_type(field.type_name)} NOT NULL" for field in entity.fields)
        if entity.relationship:
            columns.append(f"PRIMARY KEY ({', '.join(field.name for field in entity.fields)})")
        tables.append(f"CREATE TABLE IF NOT EXISTS {entity.route}(\n                {',\n                '.join(columns)}\n            );")
    return "\n            ".join(tables)


def make_model(entity: Entity) -> str:
    fields = "\n".join(f"    {field.name}: {python_type(field.type_name)}" for field in entity.fields)
    return f"class {entity.class_name}(BaseModel):\n{fields}\n"


def make_crud(entity: Entity) -> str:
    route = entity.route
    table = route
    columns = ", ".join(field.name for field in entity.fields)
    placeholders = ", ".join("?" for _ in entity.fields)
    values = ", ".join(f"item.{field.name}" for field in entity.fields)
    assignments = ", ".join(f"{field.name}=?" for field in entity.fields)
    search = " OR ".join(f"lower(CAST({field.name} AS TEXT)) LIKE ?" for field in entity.fields)
    search_args = ", ".join(f"f\"%{{search.lower()}}%\"" for _ in entity.fields)
    order = next((field.name for field in entity.fields if field.name == "name"), entity.fields[0].name)
    class_name = entity.class_name
    return f'''@app.get("/api/{route}")
def list_{route}(search: str = ""):
    with db() as con:
        rows = con.execute(
            "SELECT * FROM {table} WHERE {search} ORDER BY {order}",
            ({search_args},),
        ).fetchall()
        return [dict(row) for row in rows]


@app.post("/api/{route}")
def create_{route}(item: {class_name}):
    with db() as con:
        cur = con.execute("INSERT INTO {table}({columns}) VALUES({placeholders})", ({values},))
        return {{"id": cur.lastrowid, **item.model_dump()}}


@app.put("/api/{route}/{{item_id}}")
def update_{route}(item_id: int, item: {class_name}):
    with db() as con:
        changed = con.execute("UPDATE {table} SET {assignments} WHERE id=?", ({values}, item_id))
        if changed.rowcount == 0:
            raise HTTPException(404, "{class_name} not found")
        return {{"id": item_id, **item.model_dump()}}


@app.delete("/api/{route}/{{item_id}}")
def delete_{route}(item_id: int):
    with db() as con:
        changed = con.execute("DELETE FROM {table} WHERE id=?", (item_id,))
        if changed.rowcount == 0:
            raise HTTPException(404, "{class_name} not found")
    return {{"ok": True}}
'''


def make_relationship(entity: Entity) -> str:
    fields = entity.fields
    model = entity.class_name
    route = entity.route
    values = ", ".join(f"item.{field.name}" for field in fields)
    checks = "\n".join(
        f'''        if con.execute("SELECT 1 FROM {field.name[:-3]}s WHERE id=?", (item.{field.name},)).fetchone() is None:
            raise HTTPException(404, "Related record for {field.name} not found")'''
        for field in fields if field.name.endswith("_id")
    )
    return f'''@app.post("/api/{route}")
def create_{route}(item: {model}):
    with db() as con:
{checks}
        try:
            con.execute("INSERT INTO {route}({', '.join(field.name for field in fields)}) VALUES({', '.join('?' for _ in fields)})", ({values},))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "This relationship already exists")
    return {{"ok": True, **item.model_dump()}}
'''


def generate(spec: Spec) -> str:
    models = "\n\n".join(make_model(entity) for entity in (*spec.entities, *([spec.relationship] if spec.relationship else [])))
    crud = "\n\n".join(make_crud(entity) for entity in spec.entities)
    relationship = make_relationship(spec.relationship) if spec.relationship else ""
    return f'''from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB = Path(__file__).with_name("generated.db")


{models}

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with db() as con:
        con.executescript("""
            {make_schema(spec)}
            """)


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="Generated prototype", lifespan=lifespan)


@app.get("/")
def home():
    return {{"message": "Generated prototype", "docs": "/docs"}}


{crud}
{relationship}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("generated_main:app", host="127.0.0.1", port=8000, reload=True)
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="Markdown/text application specification")
    parser.add_argument("-o", "--output", type=Path, default=Path("generated_main.py"))
    args = parser.parse_args()
    try:
        spec = parse_spec(args.spec.read_text(encoding="utf-8"))
        args.output.write_text(generate(spec), encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()
