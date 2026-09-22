from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

DB = Path(__file__).with_name("crm.db")

class Customer(BaseModel):
    name: str
    email: str = ""
    phone: str = ""

class Product(BaseModel):
    name: str


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS customers(
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT, phone TEXT
        );
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY, name TEXT NOT NULL
        );
        """)


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(title="Tiny CRM", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.get("/api/customers")
def customers():
    with db() as con:
        return [dict(row) for row in con.execute("SELECT * FROM customers ORDER BY name")]


@app.post("/api/customers")
def add_customer(item: Customer):
    with db() as con:
        cur = con.execute("INSERT INTO customers(name,email,phone) VALUES(?,?,?)", tuple(item.model_dump().values()))
        return {"id": cur.lastrowid, **item.model_dump()}


@app.delete("/api/customers/{item_id}")
def remove_customer(item_id: int):
    with db() as con:
        if not con.execute("DELETE FROM customers WHERE id=?", (item_id,)).rowcount:
            raise HTTPException(404, "Customer not found")
    return {"ok": True}


@app.get("/api/products")
def products():
    with db() as con:
        return [dict(row) for row in con.execute("SELECT * FROM products ORDER BY name")]


@app.post("/api/products")
def add_product(item: Product):
    with db() as con:
        cur = con.execute("INSERT INTO products(name) VALUES(?)", (item.name,))
        return {"id": cur.lastrowid, "name": item.name}


@app.delete("/api/products/{item_id}")
def remove_product(item_id: int):
    with db() as con:
        if not con.execute("DELETE FROM products WHERE id=?", (item_id,)).rowcount:
            raise HTTPException(404, "Product not found")
    return {"ok": True}


HTML = """<!doctype html>
<title>Tiny CRM</title>
<style>
 body{font:16px system-ui;max-width:900px;margin:35px auto;padding:0 18px;background:#f5f7fb;color:#172033}
 main{display:grid;grid-template-columns:1fr 1fr;gap:20px}.card{background:white;padding:20px;border-radius:12px;box-shadow:0 2px 8px #0001}
 input,button{padding:9px;margin:3px;border:1px solid #ccd3df;border-radius:6px}button{cursor:pointer;background:#1769e0;color:white;border:0}
 li{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee}small{color:#667085}
 @media(max-width:650px){main{grid-template-columns:1fr}}
</style>
<h1>📇 Tiny CRM</h1><p><small>Local SQLite demo</small></p>
<main>
<section class=card><h2>Customers</h2><form id=customer><input name=name placeholder="Name" required><input name=email placeholder="Email"><input name=phone placeholder="Phone"><button>Add</button></form><ul id=customers></ul></section>
<section class=card><h2>Products</h2><form id=product><input name=name placeholder="Product name" required><button>Add</button></form><ul id=products></ul></section>
</main>
<script>
const $=s=>document.querySelector(s), esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
async function load(kind){let rows=await fetch('/api/'+kind).then(r=>r.json());$('#'+kind).innerHTML=rows.map(x=>`<li><span>${esc(x.name)}<br><small>${esc(x.email||x.phone||'')}</small></span><button onclick="del('${kind}',${x.id})">×</button></li>`).join('')||'<li><small>None yet</small></li>'}
async function del(kind,id){await fetch(`/api/${kind}/${id}`,{method:'DELETE'});load(kind)}
for(let kind of ['customers','products']){let form=$('#'+kind.slice(0,-1));form.onsubmit=async e=>{e.preventDefault();let data=Object.fromEntries(new FormData(form));await fetch('/api/'+kind,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});form.reset();load(kind)};load(kind)}
</script>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
