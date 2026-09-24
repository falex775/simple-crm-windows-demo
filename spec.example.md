# Application Spec

- Customer
- Product
- Customer Product Relationship

## Core Entities:
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

## API Endpoints:
Customer endpoints
- GET /api/customers
- GET /api/customers?search=[term]
- POST /api/customers
- PUT /api/customers/{id}
- DELETE /api/customers/{id}

Product endpoints
- GET /api/products
- GET /api/products?search=[term]
- POST /api/products
- PUT /api/products/{id}
- DELETE /api/products/{id}

Relationship endpoints
- POST /api/customer_product_relationships
