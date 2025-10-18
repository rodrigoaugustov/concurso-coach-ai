from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='../../.env', env_file_encoding='utf-8')

    DATABASE_URL: str
    
    # Novas configurações de segurança
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dias

    # Configuração do Google Cloud Storage
    GCS_BUCKET_NAME: str
    GCP_PROJECT_ID: str

    # URLs do Redis para o Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Chave de API para o Google Gemini
    GEMINI_API_KEY: str

settings = Settings()