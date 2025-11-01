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
    
    # Configurações de Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" para produção, "console" para desenvolvimento
    ENVIRONMENT: str = "development"  # "development" ou "production"
    
    @property
    def database_url(self) -> str:
        """Get database URL for external libraries."""
        return self.DATABASE_URL
    
    @property
    def gemini_api_key(self) -> str:
        """Get Gemini API key for AI services."""
        return self.GEMINI_API_KEY

settings = Settings()

def get_settings() -> Settings:
    """Get global settings instance."""
    return settings
