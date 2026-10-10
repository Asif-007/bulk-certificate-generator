
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# Store the SQLite database in the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "certificate_generator.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


# SQLite needs this setting for use with FastAPI request handling.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


# Sessions manage database operations.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


# All database models inherit from this base class.
class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
