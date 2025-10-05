import os
from dotenv import load_dotenv

load_dotenv()

def _csv_env(name: str, default: str = ""):
    raw = os.getenv(name, default)
    return [s.strip() for s in raw.split(",") if s.strip()]

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "").strip()
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("DATABASE_URL is required in backend/.env")

    CORS_ORIGINS = _csv_env("CORS_ORIGINS", "http://localhost:5173")

    PAGINATION_DEFAULT_PAGE_SIZE = int(os.getenv("PAGINATION_DEFAULT_PAGE_SIZE", "10"))
    PAGINATION_MAX_PAGE_SIZE = int(os.getenv("PAGINATION_MAX_PAGE_SIZE", "50"))

    FLASK_ENV = os.getenv("FLASK_ENV", "production")
