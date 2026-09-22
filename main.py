from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from database import create_db_and_tables
from api import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    title='Simple CRM',
    version='1.0.0',
    description='Minimal CRM demo: customers and products.'
)

app.include_router(api_router, prefix='/api')

@app.get('/')
def index():
    return {'message': 'Simple CRM API. Visit /docs for interactive docs.'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)
