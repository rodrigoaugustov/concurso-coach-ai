from __future__ import annotations
from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    # Mantém todas as variáveis existentes; apenas adiciona as novas
    ENV: str = os.getenv("ENV", "development")

    # EXISTENTES (não alterar nomes usados em outras partes)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/concurso_coach_ai")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Rate limiting (preserva chaves e só lê por ENV)
    UPLOAD_RATE_LIMIT: str = os.getenv("UPLOAD_RATE_LIMIT", "20/minute") if ENV != "production" else os.getenv("UPLOAD_RATE_LIMIT", "5/minute")
    LOGIN_RATE_LIMIT: str = os.getenv("LOGIN_RATE_LIMIT", "100/hour") if ENV != "production" else os.getenv("LOGIN_RATE_LIMIT", "10/hour")
    PLAN_GENERATION_RATE_LIMIT: str = os.getenv("PLAN_GENERATION_RATE_LIMIT", "10/minute") if ENV != "production" else os.getenv("PLAN_GENERATION_RATE_LIMIT", "2/minute")

    class Config:
        env_file = ".env"

# Fornece função get_settings para compatibilidade com importações existentes
_settings_singleton: Settings | None = None

def get_settings() -> Settings:
    global _settings_singleton
    if _settings_singleton is None:
        _settings_singleton = Settings()
    return _settings_singleton

settings = get_settings()
