"""
database.py — SQLAlchemy engine, session factory, declarative base, and FastAPI dependency.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# Load environment variables from backend/.env
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set — check backend/.env")

# ---------------------------------------------------------------------------
# Engine — a single connection pool shared across the application
# ---------------------------------------------------------------------------
engine = create_engine(DATABASE_URL)

# ---------------------------------------------------------------------------
# SessionLocal — each request gets its own short-lived session
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Base — all ORM model classes inherit from this to get table-mapping support
# ---------------------------------------------------------------------------
Base = declarative_base()

# ---------------------------------------------------------------------------
# get_db — FastAPI dependency that yields a session and guarantees cleanup
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
