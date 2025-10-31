# backend/app/core/constants.py

"""
Constantes centralizadas para eliminar magic numbers no projeto.

Esta arquivo centraliza todos os valores hardcoded encontrados no código,
organizados por categoria de funcionalidade.
"""


class CeleryConstants:
    """Constantes para configuração do Celery"""
    RETRY_BACKOFF_SECONDS = 5  # Tempo de espera entre tentativas
    SOFT_TIME_LIMIT_SECONDS = 300  # 5 minutos - limite soft
    HARD_TIME_LIMIT_SECONDS = 600  # 10 minutos - limite hard
    MAX_RETRIES = 3  # Número máximo de tentativas


class AIConstants:
    """Constantes para configuração da IA"""
    TEMPERATURE_CREATIVE = 1.0  # Para extração criativa de editais
    TEMPERATURE_PRECISE = 0.2   # Para validação precisa
    TEMPERATURE_BALANCED = 0.5  # Para planejamento de estudos
    
    # Limites de validação para IA
    MAX_RETRIES_AI_VALIDATION = 2  # Máximo de tentativas de correção
    MAX_SESSIONS_ESTIMATE = 10     # Máximo de sessões por tópico
    

class RateLimitConstants:
    """Constantes para rate limiting"""
    UPLOAD_RATE_LIMIT = "5/minute"
    LOGIN_RATE_LIMIT = "10/hour"
    PLAN_GENERATION_RATE_LIMIT = "2/minute"
    GENERAL_API_RATE_LIMIT = "100/minute"


class DatabaseConstants:
    """Constantes para configuração do banco"""
    CONNECTION_POOL_SIZE = 10
    CONNECTION_POOL_MAX_OVERFLOW = 20
    CONNECTION_POOL_RECYCLE_SECONDS = 3600  # 1 hora


class ValidationConstants:
    """Constantes para validação de dados"""
    MAX_PDF_SIZE_MB = 50
    MAX_PASSWORD_LENGTH = 128
    MIN_PASSWORD_LENGTH = 8
    MAX_SESSIONS_ESTIMATE = 10  # Máximo de sessões estimadas por tópico
    
    # Fatores de cálculo de sessões de estudo
    SESSIONS_PER_DAY = 2  # Duas sessões por dia até a prova
    

class StudyPlanConstants:
    """Constantes específicas para geração de planos de estudo"""
    DEFAULT_IMPACT_WEIGHT = 1.0  # Peso padrão quando não há estrutura de prova definida
    
    # Timeouts para diferentes fases do pipeline
    DATA_COLLECTION_TIMEOUT_MS = 5000   # 5 segundos
    AI_ANALYSIS_TIMEOUT_MS = 30000      # 30 segundos
    AI_ORGANIZATION_TIMEOUT_MS = 30000  # 30 segundos
    DATABASE_PERSISTENCE_TIMEOUT_MS = 10000  # 10 segundos


class FileProcessingConstants:
    """Constantes para processamento de arquivos"""
    SUPPORTED_FILE_TYPES = ["application/pdf"]
    BASE64_CHUNK_SIZE = 1024 * 1024  # 1MB chunks para processamento
    
    # Timeouts para diferentes etapas do processamento
    DOWNLOAD_TIMEOUT_MS = 60000      # 1 minuto
    AI_EXTRACTION_TIMEOUT_MS = 120000  # 2 minutos
    AI_REFINEMENT_TIMEOUT_MS = 90000   # 1.5 minutos
    VALIDATION_TIMEOUT_MS = 5000       # 5 segundos
    PERSISTENCE_TIMEOUT_MS = 30000     # 30 segundos


class SecurityConstants:
    """Constantes de segurança"""
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
    BCRYPT_ROUNDS = 12
    
    # Rate limiting específico para autenticação
    LOGIN_ATTEMPTS_LIMIT = 5
    LOGIN_LOCKOUT_MINUTES = 15


class LoggingConstants:
    """Constantes para configuração de logs"""
    MAX_LOG_MESSAGE_LENGTH = 2048
    LOG_ROTATION_SIZE_MB = 10
    LOG_RETENTION_DAYS = 30
    
    # Níveis de log estruturado
    PERFORMANCE_THRESHOLD_MS = 1000  # Log como warning se operação > 1s
    SLOW_QUERY_THRESHOLD_MS = 500    # Log queries lentas
