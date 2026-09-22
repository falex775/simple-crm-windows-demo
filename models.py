from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class CustomerProductLink(SQLModel, table=True):
    customer_id: Optional[int] = Field(default=None, foreign_key='customer.id', primary_key=True)
    product_id: Optional[int] = Field(default=None, foreign_key='product.id', primary_key=True)

class ProductBase(SQLModel):
    name: str

class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customers: List['Customer'] = Relationship(back_populates='products', link_model=CustomerProductLink)

class ProductCreate(ProductBase):
    pass

class ProductRead(ProductBase):
    id: int

class CustomerBase(SQLModel):
    name: str
    email: str
    phone: Optional[str] = None

class Customer(CustomerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    products: List[Product] = Relationship(back_populates='customers', link_model=CustomerProductLink)

class CustomerCreate(CustomerBase):
    pass

class CustomerRead(CustomerBase):
    id: int
    products: List[ProductRead] = []
