from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.base import Base
import os
from dotenv import load_dotenv
import models 
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv() 
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL",)
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:  # type: ignore[misc]

    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)