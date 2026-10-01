'''
Database setup: engine, session factory, declarative Base, and a transaction
context manager.

  - DATABASE_URL comes from .env (loaded once here).
  - echo is driven by the SQL_ECHO env var (default off; debug only).
  - transaction() is the primary entry point — an atomic unit of work that commits
    on success, rolls back on error, and always closes the session.
'''

import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# Load .env so DATABASE_URL is available before the engine is created.
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://analyst:analyst123@localhost:5433/document_analyst",
)
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() in {"1", "true", "yes"}

# pool_pre_ping recycles dead connections; echo logs SQL only when debugging.
engine = create_engine(DATABASE_URL, echo=SQL_ECHO, pool_pre_ping=True)

# autocommit=False is important — we control commits explicitly via transaction().
# expire_on_commit=False keeps ORM objects usable after the transaction() block
# commits and closes (so callers can read e.g. doc.id outside the `with`).
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)

Base = declarative_base()


@contextmanager
def transaction() -> Generator[Session, None, None]:
    '''
    Atomic unit of work: commit on success, rollback on exception, always close.

    Usage:
        with transaction() as db:
            repo = DocumentRepository(db)
            repo.create(...)
        # commit + close happen automatically here
    '''
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
