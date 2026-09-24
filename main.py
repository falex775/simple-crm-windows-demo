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


class CustomerProductLink(BaseModel):
    customer_id: int
    product_id: int


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT
            );
            CREATE TABLE IF NOT EXISTS products(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS customer_products(
                customer_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                PRIMARY KEY (customer_id, product_id),
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );
            """
        )


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="Tiny CRM", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.get("/api/customers")
def customers(search: str = ""):
    with db() as con:
        rows = con.execute(
            "SELECT * FROM customers WHERE lower(name) LIKE ? OR lower(email) LIKE ? OR lower(phone) LIKE ? ORDER BY name",
            (f"%{search.lower()}%", f"%{search.lower()}%", f"%{search.lower()}%"),
        ).fetchall()
        return [dict(row) for row in rows]


@app.post("/api/customers")
def add_customer(item: Customer):
    with db() as con:
        cur = con.execute(
            "INSERT INTO customers(name,email,phone) VALUES(?,?,?)",
            (item.name, item.email, item.phone),
        )
        return {"id": cur.lastrowid, **item.model_dump()}


@app.put("/api/customers/{item_id}")
def update_customer(item_id: int, item: Customer):
    with db() as con:
        changed = con.execute(
            "UPDATE customers SET name=?, email=?, phone=? WHERE id=?",
            (item.name, item.email, item.phone, item_id),
        )
        if changed.rowcount == 0:
            raise HTTPException(404, "Customer not found")
        return {"id": item_id, **item.model_dump()}


@app.delete("/api/customers/{item_id}")
def remove_customer(item_id: int):
    with db() as con:
        changed = con.execute("DELETE FROM customers WHERE id=?", (item_id,))
        if changed.rowcount == 0:
            raise HTTPException(404, "Customer not found")
    return {"ok": True}


@app.get("/api/products")
def products(search: str = ""):
    with db() as con:
        rows = con.execute(
            "SELECT * FROM products WHERE lower(name) LIKE ? ORDER BY name",
            (f"%{search.lower()}%",),
        ).fetchall()
        return [dict(row) for row in rows]


@app.post("/api/products")
def add_product(item: Product):
    with db() as con:
        cur = con.execute("INSERT INTO products(name) VALUES(?)", (item.name,))
        return {"id": cur.lastrowid, "name": item.name}


@app.put("/api/products/{item_id}")
def update_product(item_id: int, item: Product):
    with db() as con:
        changed = con.execute("UPDATE products SET name=? WHERE id=?", (item.name, item_id))
        if changed.rowcount == 0:
            raise HTTPException(404, "Product not found")
        return {"id": item_id, "name": item.name}


@app.delete("/api/products/{item_id}")
def remove_product(item_id: int):
    with db() as con:
        changed = con.execute("DELETE FROM products WHERE id=?", (item_id,))
        if changed.rowcount == 0:
            raise HTTPException(404, "Product not found")
    return {"ok": True}


@app.post("/api/links")
def link_customer_product(item: CustomerProductLink):
    with db() as con:
        customer = con.execute("SELECT id FROM customers WHERE id=?", (item.customer_id,)).fetchone()
        if customer is None:
            raise HTTPException(404, "Customer not found")
        product = con.execute("SELECT id FROM products WHERE id=?", (item.product_id,)).fetchone()
        if product is None:
            raise HTTPException(404, "Product not found")
        try:
            con.execute(
                "INSERT INTO customer_products(customer_id, product_id) VALUES(?, ?)",
                (item.customer_id, item.product_id),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Customer is already linked to this product")
    return {"ok": True, **item.model_dump()}


@app.get("/api/customers/{customer_id}/products")
def customer_products(customer_id: int):
    with db() as con:
        customer = con.execute("SELECT id FROM customers WHERE id=?", (customer_id,)).fetchone()
        if customer is None:
            raise HTTPException(404, "Customer not found")
        rows = con.execute(
            """
            SELECT p.id, p.name
            FROM products p
            JOIN customer_products cp ON cp.product_id = p.id
            WHERE cp.customer_id = ?
            ORDER BY p.name
            """,
            (customer_id,),
        ).fetchall()
        return [dict(row) for row in rows]


@app.delete("/api/links")
def unlink_customer_product(item: CustomerProductLink):
    with db() as con:
        changed = con.execute(
            "DELETE FROM customer_products WHERE customer_id=? AND product_id=?",
            (item.customer_id, item.product_id),
        )
        if changed.rowcount == 0:
            raise HTTPException(404, "Link not found")
    return {"ok": True}


HTML = """<!doctype html>
<title>Tiny CRM</title>
<style>
body{font:16px system-ui;max-width:980px;margin:30px auto;padding:0 16px;background:#f4f7fb;color:#18212f}
main{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.card{background:#fff;border-radius:12px;padding:18px;box-shadow:0 2px 10px rgba(15,23,42,.08)}
input,button,select{padding:9px 10px;border-radius:8px;border:1px solid #cdd8e4;font-size:15px}
input{width:100%;box-sizing:border-box;margin:4px 0}
button{cursor:pointer;background:#1d6fe8;color:white;border:0;min-width:80px;margin:2px}
button.secondary{background:#e9edf5;color:#172033;border:1px solid #d3dae5}
button.danger{background:#d93b3b}
form{display:grid;gap:6px}
.row{display:flex;gap:8px;align-items:center}
.search{margin-bottom:10px}
ul{list-style:none;padding:0;margin:10px 0 0}
li{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #edf1f5}
small{color:#667085}
.hidden{display:none}
#linkedProductsPanel ul{margin-top:8px}
@media(max-width:700px){main{grid-template-columns:1fr}#linkForm{grid-template-columns:1fr!important}}
</style>
<h1>📇 Tiny CRM</h1>
<p><small>SQLite demo with create, edit, delete and search</small></p>
<main>
  <section class="card">
    <h2>Customers</h2>
    <input class="search" id="customersSearch" placeholder="Search customers..." />
    <form id="customersForm">
      <input type="hidden" name="id">
      <input name="name" placeholder="Customer name" required>
      <input name="email" placeholder="Email">
      <input name="phone" placeholder="Phone">
      <div class="row">
        <button type="submit">Save</button>
        <button type="button" class="secondary hidden" id="customersCancel">Cancel</button>
      </div>
    </form>
    <ul id="customersList"></ul>
  </section>

  <section class="card">
    <h2>Products</h2>
    <input class="search" id="productsSearch" placeholder="Search products..." />
    <form id="productsForm">
      <input type="hidden" name="id">
      <input name="name" placeholder="Product name" required>
      <div class="row">
        <button type="submit">Save</button>
        <button type="button" class="secondary hidden" id="productsCancel">Cancel</button>
      </div>
    </form>
    <ul id="productsList"></ul>
  </section>
</main>
<section class="card" style="margin-top:20px">
  <h2>Link customer ↔ product</h2>
  <form id="linkForm" style="grid-template-columns:1fr 1fr auto;display:grid;gap:8px;align-items:center">
    <select id="linkCustomer" required></select>
    <select id="linkProduct" required></select>
    <button type="submit" class="link">Link</button>
  </form>
  <small id="linkMessage"></small>
</section>
<section class="card" id="linkedProductsPanel" style="margin-top:20px">
  <h2>Linked products</h2>
  <select id="linkedProductsCustomer" aria-label="Choose a customer"></select>
  <ul id="linkedProductsList"></ul>
</section>
<script>
const state = { customers: [], products: [] };
const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

function renderList(kind, rows) {
  const list = $(kind + 'List');
  const q = ($(kind + 'Search').value || '').trim().toLowerCase();
  const filtered = rows.filter(row => JSON.stringify(Object.values(row)).toLowerCase().includes(q));
  if (!filtered.length) {
    list.innerHTML = '<li><small>No results</small></li>';
    return;
  }
  const isCustomer = kind === 'customers';
  list.innerHTML = filtered.map(row => `
    <li>
      <span>${esc(isCustomer ? (row.name || '') : row.name)}${isCustomer ? `<br><small>${esc(row.email || '')}${row.email && row.phone ? ' • ' : ''}${esc(row.phone || '')}</small>` : ''}</span>
      <span class="row">
        <button type="button" class="secondary" onclick="edit('${kind}', ${row.id})">Edit</button>
        <button type="button" class="danger" onclick="del('${kind}', ${row.id})">Delete</button>
      </span>
    </li>`).join('');
}

function renderLinkOptions() {
  const customerOptions = state.customers.length
    ? state.customers.map(row => `<option value="${row.id}">${esc(row.name)}</option>`).join('')
    : '<option value="">Add a customer first</option>';
  $('linkCustomer').innerHTML = customerOptions;
  $('linkedProductsCustomer').innerHTML = customerOptions;
  $('linkProduct').innerHTML = state.products.length
    ? state.products.map(row => `<option value="${row.id}">${esc(row.name)}</option>`).join('')
    : '<option value="">Add a product first</option>';
  if (state.customers.length) loadLinkedProducts();
  else $('linkedProductsList').innerHTML = '<li><small>Add a customer first</small></li>';
}

async function load(kind) {
  const q = ($(kind + 'Search').value || '').trim();
  const rows = await fetch('/api/' + kind + (q ? '?search=' + encodeURIComponent(q) : '')).then(r => r.json());
  state[kind] = rows;
  renderList(kind, rows);
  renderLinkOptions();
}

async function loadLinkedProducts() {
  const customerId = Number($('linkedProductsCustomer').value);
  const list = $('linkedProductsList');
  if (!customerId) {
    list.innerHTML = '<li><small>Select a customer to see linked products</small></li>';
    return;
  }
  const response = await fetch('/api/customers/' + customerId + '/products');
  const rows = await response.json();
  if (!rows.length) {
    list.innerHTML = '<li><small>No products linked to this customer</small></li>';
    return;
  }
  list.innerHTML = rows.map(row => `
    <li>
      <span>${esc(row.name)}</span>
      <button type="button" class="danger" onclick="unlinkProduct(${customerId}, ${row.id})">Unlink</button>
    </li>`).join('');
}

async function unlinkProduct(customerId, productId) {
  const response = await fetch('/api/links', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_id: customerId, product_id: productId })
  });
  if (!response.ok) {
    const result = await response.json();
    $('linkMessage').textContent = result.detail || 'Could not remove link.';
    return;
  }
  $('linkMessage').textContent = 'Link removed.';
  loadLinkedProducts();
}

function resetForm(kind) {
  const form = $(kind + 'Form');
  form.reset();
  form.querySelector('[name="id"]').value = '';
  $(kind + 'Cancel').classList.add('hidden');
}

function edit(kind, id) {
  const row = state[kind].find(x => x.id === id);
  if (!row) return;
  const form = $(kind + 'Form');
  form.querySelector('[name="id"]').value = row.id;
  Object.keys(row).forEach(key => {
    const field = form.querySelector('[name="' + key + '"]');
    if (field) field.value = row[key] ?? '';
  });
  $(kind + 'Cancel').classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function del(kind, id) {
  if (!confirm('Delete this item?')) return;
  await fetch('/api/' + kind + '/' + id, { method: 'DELETE' });
  resetForm(kind);
  load(kind);
}

async function submitForm(kind, event) {
  event.preventDefault();
  const form = event.target;
  const data = Object.fromEntries(new FormData(form).entries());
  const id = data.id;
  delete data.id;
  const method = id ? 'PUT' : 'POST';
  const url = '/api/' + kind + (id ? '/' + id : '');
  await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  resetForm(kind);
  load(kind);
}

$('linkForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = $('linkMessage');
  const response = await fetch('/api/links', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer_id: Number($('linkCustomer').value),
      product_id: Number($('linkProduct').value)
    })
  });
  const result = await response.json();
  message.textContent = response.ok ? 'Customer and product linked.' : (result.detail || 'Could not create link.');
  if (response.ok) {
    $('linkedProductsCustomer').value = $('linkCustomer').value;
    loadLinkedProducts();
  }
});

$('linkedProductsCustomer').addEventListener('change', loadLinkedProducts);

['customers', 'products'].forEach(kind => {
  const form = $(kind + 'Form');
  form.addEventListener('submit', (e) => submitForm(kind, e));
  $(kind + 'Cancel').addEventListener('click', () => resetForm(kind));
  $(kind + 'Search').addEventListener('input', () => load(kind));
  load(kind);
});

window.edit = edit;
window.del = del;
window.unlinkProduct = unlinkProduct;
</script>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
