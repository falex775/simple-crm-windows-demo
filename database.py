from sqlmodel import SQLModel, create_engine, Session
import os

database_url = os.getenv('DATABASE_URL', 'sqlite:///crm.db')
engine = create_engine(
    database_url,
    connect_args={'check_same_thread': False} if 'sqlite' in database_url else {},
    echo=False
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
