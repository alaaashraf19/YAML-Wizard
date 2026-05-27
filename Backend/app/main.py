# # from fastapi import FastAPI
# # from routers import auth_router
#
# app = FastAPI()
# app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
#
# import logging
#
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
#
# from app.core.config import settings
# from app.routers import agent_router, auth_router   # auth_router = existing
#
# logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
#
# app = FastAPI(
#     title=settings.app_title,
#     description="Intelligent repository context extraction for CI/CD YAML generation.",
#     version="0.2.0",
#     debug=settings.debug,
# )
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
#
# # Routers
# app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
# app.include_router(agent_router.router)
#
#
# @app.get("/health", tags=["meta"])
# def health() -> dict:
#     return {"status": "ok"}

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth_router
from routers import agent_router

app = FastAPI(
    title="YAML Wizard API",
    version="0.2.0",
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
def health():
    return {"status": "ok"}

from database.db_engine import create_tables
create_tables()