from fastapi import FastAPI
from routers import auth_router,project_router,chatbot_router
from database.db_engine import create_tables

create_tables()
app = FastAPI()
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(project_router.router, prefix="/projects", tags=["projects"])

app.include_router(chatbot_router.router, prefix="/chatbot", tags=["chatbot"])