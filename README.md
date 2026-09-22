# Tiny CRM Windows Demo

A minimal, single-file CRM based on the original FastAPI/SQLModel project. It keeps only customers, products, a small browser UI, and a local SQLite database.

## Windows

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py main.py
```

Open http://127.0.0.1:8000. The database is created automatically as `crm.db` beside `main.py`.

## API

- `GET/POST/DELETE /api/customers`
- `GET/POST/DELETE /api/products`
- `/docs` provides the generated API documentation.

`main.py` is the complete single-file version: no Docker, PostgreSQL, migrations, templates, static files, authentication, or SQLModel setup is required.
