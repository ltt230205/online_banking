import asyncio
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings


if sys.platform == "win32":
    # psycopg's async connection does not support Windows' default Proactor loop.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# The synchronous engine remains for Alembic/seed/test setup. API requests use
# one AsyncSession each, backed by psycopg's asyncio dialect.
async_engine = create_async_engine(settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)
