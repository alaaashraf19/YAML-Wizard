import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import auth_router, agent_router
from database.db_engine import create_tables

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

app = FastAPI(
    title=settings.app_title,
    description="Intelligent repository context extraction for CI/CD YAML generation.",
    version="0.3.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(agent_router.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


create_tables()
