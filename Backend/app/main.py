from contextlib import asynccontextmanager

from fastapi import FastAPI
from database.db_engine import create_tables
from middleware.middleware import setup_middleware
from routers import auth_router, github_app_router, github_connect_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(lifespan=lifespan)

setup_middleware(app)


app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(github_app_router.router, prefix="/github", tags=["github"])
app.include_router(github_connect_router.router, prefix="/github_account", tags=["github_connect"])