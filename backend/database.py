"""
Database configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from runtime_config import get_database_url, get_env_file

load_dotenv(get_env_file())

DATABASE_URL = get_database_url()

# SQLite specific connect args
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    import models as db_models  # noqa
    Base.metadata.create_all(bind=engine, checkfirst=True)
