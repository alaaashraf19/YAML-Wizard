from contextlib import asynccontextmanager
from fastapi import FastAPI
from database.db_engine import create_tables
from middleware.middleware import setup_middleware
from routers import auth_router, github_app_router, publisher_router,platfroms_connect_router, chatbot_router, project_router, agent_router
from routers.dashboard import repos_router, runs_router, tests_router, insights_router
from realtime import websocket_router
import asyncio
from services.dashboard.sync_loop_service import background_sync_loop
from services.dashboard.test_parsers.loader import load_parsers
import logging
import sys
import os
from core.config import settings

sys.path.insert(0, os.path.dirname(__file__))
# logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")



_sync_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    """Startup: init DB tables, start background sync. Shutdown: cleanup."""
    
    global _sync_task
    await create_tables()
    load_parsers()
    _sync_task = asyncio.create_task(background_sync_loop())
    yield
    if _sync_task:
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    lifespan=lifespan,
    title=settings.app_title,
    version="0.3.0",
    debug=settings.debug,
)

setup_middleware(app)


    
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(project_router.router, prefix="/projects", tags=["projects"])
app.include_router(chatbot_router.router, prefix="/chatbot", tags=["chatbot"])
app.include_router(github_app_router.router, prefix="/github", tags=["github_app"])
app.include_router(platfroms_connect_router.router, prefix="/platform", tags=["platform_connect"])
app.include_router(publisher_router.router, prefix="/publish", tags=["publish_yaml"])

app.include_router(repos_router.router, prefix="/dashboard", tags=["dashboard_repositories"])
app.include_router(runs_router.router, prefix="/dashboard", tags=["dashboard_repo_runs"])
app.include_router(tests_router.router, prefix="/dashboard", tags=["dashboard_repo_runs_tests"])
app.include_router(insights_router.router, prefix="/dashboard", tags=["dashboard_insights"])

app.include_router(websocket_router.router, prefix="/realtime", tags=["realtime_updates"])

app.include_router(agent_router.router)

@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}




