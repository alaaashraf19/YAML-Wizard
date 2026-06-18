from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.base import Base
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    # Import all models so SQLAlchemy registers them before create_all
    import models.user_model  # noqa: F401
    import models.repo_model  # noqa: F401
    Base.metadata.create_all(bind=engine)
