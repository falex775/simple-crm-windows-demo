# Simple CRM - Windows Demo

A minimal, lightweight CRM demo built with **FastAPI**, **SQLModel**, and **SQLite**.

## Features

- ✨ Manage customers and products
- 🗄️ SQLite database (zero setup, no Docker needed)
- 📖 Auto-generated interactive API docs (Swagger UI)
- 🚀 Runs natively on Windows
- 📦 ~50 lines of application code

## Quick Start

### 1. Install Python (3.10+)
Download from [python.org](https://www.python.org/)

### 2. Setup

```bash
# Clone or download this repo
git clone https://github.com/falex775/simple-crm-windows-demo.git
cd simple-crm-windows-demo

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run

```bash
python main.py
```

The API starts at **http://127.0.0.1:8000**

### 4. Try it out

- **Interactive docs**: http://127.0.0.1:8000/docs (Swagger UI)
- **ReDoc**: http://127.0.0.1:8000/redoc

## API Endpoints

### Customers
- `GET /api/customers` – List all customers
- `POST /api/customers` – Create a customer
- `GET /api/customers/{id}` – Get one customer
- `DELETE /api/customers/{id}` – Delete a customer
- `POST /api/customers/{id}/products/{product_id}` – Link product to customer

### Products
- `GET /api/products` – List all products
- `POST /api/products` – Create a product
- `GET /api/products/{id}` – Get one product
- `DELETE /api/products/{id}` – Delete a product

## Example Usage

```bash
# Create a customer
curl -X POST http://127.0.0.1:8000/api/customers -H "Content-Type: application/json" -d '{"name": "John Doe", "email": "john@example.com", "phone": "555-1234"}'

# Create a product
curl -X POST http://127.0.0.1:8000/api/products -H "Content-Type: application/json" -d '{"name": "Widget"}'

# Link customer to product
curl -X POST http://127.0.0.1:8000/api/customers/1/products/1

# List customers
curl http://127.0.0.1:8000/api/customers
```

## Database

Database file: `crm.db` (auto-created on first run)

To reset: Delete `crm.db` and restart the app.

## Project Structure

```
.
├── main.py           # Application entry point
├── database.py       # SQLite setup
├── models.py         # Customer & Product schemas
├── api.py            # REST API endpoints
├── requirements.txt  # Python dependencies
└── README.md
```

## License

MIT
