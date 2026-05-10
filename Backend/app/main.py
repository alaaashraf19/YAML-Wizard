from contextlib import asynccontextmanager
from fastapi import FastAPI
from database.db_engine import create_tables
from middleware.middleware import setup_middleware
from routers import auth_router, github_app_router, publisher_router,platfroms_connect_router
from routers.dashboard import repos_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(lifespan=lifespan)

setup_middleware(app)


app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(github_app_router.router, prefix="/github", tags=["github_app"])
app.include_router(platfroms_connect_router.router, prefix="/platform", tags=["platform_connect"])
app.include_router(publisher_router.router, prefix="/publish", tags=["publish_yaml"])

app.include_router(repos_router.router, prefix="/dashboard/repos", tags=["dashboard_repositories"])