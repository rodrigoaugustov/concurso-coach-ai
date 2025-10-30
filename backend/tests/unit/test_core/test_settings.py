import os
import pytest
from app.core.settings import Settings


def test_settings_loads_with_defaults(monkeypatch):
    # Define mínimos exigidos
    env = {
        "DATABASE_URL": "postgresql+psycopg2://u:p@localhost:5432/db",
        "JWT_SECRET_KEY": "secret",
        "GCS_BUCKET_NAME": "bucket",
        "GCP_PROJECT_ID": "proj",
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
        "GEMINI_API_KEY": "abc",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    s = Settings()
    assert s.JWT_ALGORITHM == "HS256"
    assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24 * 7
    # Defaults de logging (adicionados previamente)
    assert s.LOG_LEVEL in ("INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL")
    assert s.ENVIRONMENT in ("development", "production")


def test_settings_missing_required(monkeypatch):
    # Limpa variáveis
    for k in list(os.environ.keys()):
        if k in {
            "DATABASE_URL","JWT_SECRET_KEY","GCS_BUCKET_NAME","GCP_PROJECT_ID",
            "CELERY_BROKER_URL","CELERY_RESULT_BACKEND","GEMINI_API_KEY"
        }:
            monkeypatch.delenv(k, raising=False)

    with pytest.raises(Exception):
        Settings()
