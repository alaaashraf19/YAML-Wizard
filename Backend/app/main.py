from fastapi import FastAPI
from contextlib import asynccontextmanager
from routers import auth_router
from database.db_engine import create_tables
from middleware.middleware import setup_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(lifespan=lifespan)

setup_middleware(app)

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])