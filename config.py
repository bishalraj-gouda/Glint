import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _resolve_database_uri() -> tuple:
    """Resolves database URI from environment with resilient fallback to local SQLite."""
    db_dir = BASE_DIR / "instance"
    try:
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "placementiq.db"
    except OSError:
        # Fallback to /tmp in read-only serverless environments (Vercel / AWS Lambda)
        db_path = Path("/tmp") / "placementiq.db"
    sqlite_fallback = f"sqlite:///{db_path}"

    raw_url = os.getenv("DATABASE_URL", "").strip()

    # Fall back to SQLite if not configured or if placeholder still present
    if not raw_url or "[YOUR_DATABASE_PASSWORD]" in raw_url:
        return sqlite_fallback, {}

    # Normalize deprecated postgres:// prefix to postgresql://
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    # Engine options for cloud-hosted PostgreSQL (Supabase / PgBouncer)
    engine_options = {
        "pool_pre_ping": True,  # Verifies connection liveness before execution
        "pool_recycle": 300,    # Recycles connections every 5 mins to prevent stale sockets
        "pool_size": 10,
        "max_overflow": 20,
    }

    return raw_url, engine_options


_RESOLVED_DB_URI, _RESOLVED_ENGINE_OPTIONS = _resolve_database_uri()


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-fallback-38493021")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = _RESOLVED_DB_URI
    SQLALCHEMY_ENGINE_OPTIONS = _RESOLVED_ENGINE_OPTIONS

    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://oxjxpkwkrtbidvfwfvuq.supabase.co")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # AI Engine Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    AI_DEMO_MODE = os.getenv("AI_DEMO_MODE", "true").lower() in ("true", "1", "yes")

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production" or bool(os.getenv("VERCEL"))


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration with in-memory database."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

