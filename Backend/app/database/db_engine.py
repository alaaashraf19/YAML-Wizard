from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.base import Base
import os
from dotenv import load_dotenv
import models 

load_dotenv() 
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL",)
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")
engine = create_engine(SQLALCHEMY_DATABASE_URL)

#session maker help us perform actions on our database
#unless we specify we want to autocommit or autoflush, we need to call commit() and flush() manually after performing actions on the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal() #initilaize a new session
    try:
        yield db
    finally:
        db.close()

def create_tables():

    Base.metadata.create_all(bind=engine)