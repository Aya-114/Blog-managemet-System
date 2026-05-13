import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings:
    app_name: str = os.getenv("APP_NAME", "Blog Management System")
    api_prefix: str = "/api/v1"
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'blog.db'}")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_backend: str = os.getenv("CACHE_BACKEND", "redis")
    log_file: str = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "app.log"))


settings = Settings()
