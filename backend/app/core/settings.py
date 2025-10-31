import os
from functools import lru_cache
from pydantic import BaseSettings

class Settings(BaseSettings):
    ENV: str = os.getenv("ENV", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/concurso_coach_ai")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Rate limiting defaults (podem ser ajustados por ENV)
    UPLOAD_RATE_LIMIT: str = "20/minute" if ENV != "production" else "5/minute"
    LOGIN_RATE_LIMIT: str = "100/hour" if ENV != "production" else "10/hour"
    PLAN_GENERATION_RATE_LIMIT: str = "10/minute" if ENV != "production" else "2/minute"

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
