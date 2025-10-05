from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import Config

# Engine
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    future=True,
    pool_pre_ping=True,
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
)

# Declarative Base
class Base(DeclarativeBase):
    pass

def init_db():
    # Import models to register tables
    from models import job  # noqa: F401
    Base.metadata.create_all(bind=engine)
