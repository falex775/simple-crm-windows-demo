from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import (
    Customer, CustomerCreate, CustomerRead,
    Product, ProductCreate, ProductRead
)
from typing import List

router = APIRouter()

# Customers
@router.get('/customers', response_model=List[CustomerRead])
def get_customers(session: Session = Depends(get_session)):
    customers = session.exec(select(Customer)).all()
    return customers

@router.post('/customers', response_model=CustomerRead)
def create_customer(customer: CustomerCreate, session: Session = Depends(get_session)):
    db_customer = Customer.model_validate(customer)
    session.add(db_customer)
    session.commit()
    session.refresh(db_customer)
    return db_customer

@router.get('/customers/{customer_id}', response_model=CustomerRead)
def get_customer(customer_id: int, session: Session = Depends(get_session)):
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    return customer

@router.delete('/customers/{customer_id}')
def delete_customer(customer_id: int, session: Session = Depends(get_session)):
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    session.delete(customer)
    session.commit()
    return {'ok': True}

# Products
@router.get('/products', response_model=List[ProductRead])
def get_products(session: Session = Depends(get_session)):
    products = session.exec(select(Product)).all()
    return products

@router.post('/products', response_model=ProductRead)
def create_product(product: ProductCreate, session: Session = Depends(get_session)):
    db_product = Product.model_validate(product)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product

@router.get('/products/{product_id}', response_model=ProductRead)
def get_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail='Product not found')
    return product

@router.delete('/products/{product_id}')
def delete_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail='Product not found')
    session.delete(product)
    session.commit()
    return {'ok': True}

# Link customer to product
@router.post('/customers/{customer_id}/products/{product_id}')
def add_product_to_customer(customer_id: int, product_id: int, session: Session = Depends(get_session)):
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail='Customer not found')
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail='Product not found')
    if product not in customer.products:
        customer.products.append(product)
        session.add(customer)
        session.commit()
        session.refresh(customer)
    return customer
