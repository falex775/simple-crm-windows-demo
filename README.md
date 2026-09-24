# Tiny CRM Windows Demo

A minimal, single-file CRM based on FastAPI and SQLite.

## Windows

```cmd
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
py main.py
```

Open http://127.0.0.1:8000. The database is created automatically as `crm.db` beside `main.py`.

## Generate a prototype from a specification

`generate_app.py` reads the Markdown-like application specification format and writes a standalone FastAPI/SQLite prototype. It supports multiple CRUD entities and one many-to-many relationship with a uniqueness constraint.

```cmd
py generate_app.py spec.example.md --output generated_main.py
py generated_main.py
```

The generated application uses `generated.db`, exposes the CRUD and relationship endpoints described by the spec, and includes FastAPI documentation at http://127.0.0.1:8000/docs. Field types currently supported are `string`/`text`, `integer`/`int`, `float`/`number`/`decimal`, and `boolean`/`bool`; unknown types are treated as text.

The original hand-written demo remains in `main.py`; generated files can be discarded and regenerated at any time.

## API

- `GET/POST/PUT/DELETE /api/customers`
- `GET/POST/PUT/DELETE /api/products`
- `POST /api/links`
- `/docs` provides the generated API documentation.
