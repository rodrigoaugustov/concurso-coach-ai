from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.database import engine
from app import models
from app.users.router import router as users_router
from app.contests.router import router as contests_router
from app.study.router import router as study_router
from app.guided_lesson.router import router as guided_lesson_router
from app.core.exceptions import CoachAIException
from app.core.exception_handlers import (
    coach_ai_exception_handler,
    validation_exception_handler,
)
from app.core.middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware
from app.core.settings import settings
from app.core.logging import setup_logging, get_logger

# Configura o sistema de logging estruturado
setup_logging(
    log_level=settings.LOG_LEVEL,
    is_development=(settings.ENVIRONMENT == "development")
)

# Logger para o módulo main
logger = get_logger("main")

# Rate limiting (lazy import to avoid optional dep crash)
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
    USE_RATE_LIMIT = True
    logger.info("Rate limiting enabled")
except Exception as e:
    limiter = None
    USE_RATE_LIMIT = False
    logger.warning("Rate limiting disabled", error=str(e))

# Cria as tabelas no banco de dados
logger.info("Creating database tables")
models.Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully")

app = FastAPI(
    title="Concurso Coach AI API",
    description="A API para a plataforma de estudos para concursos.",
    version="0.1.0"
)

# Lista de origens que têm permissão para fazer requisições à nossa API
origins = [
    "http://localhost",
    "http://localhost:3000",  # Desenvolvimento local
    "https://frontend-production-f6ac.up.railway.app",  # Frontend em produção no Railway
]

logger.info("Configuring CORS middleware", allowed_origins=origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware (deve ser adicionado antes de outros middlewares)
logger.info("Adding request logging middleware")
app.add_middleware(RequestLoggingMiddleware)

# Security headers middleware
logger.info("Adding security headers middleware")
app.add_middleware(SecurityHeadersMiddleware)

# Exception handlers
logger.info("Configuring exception handlers")
app.add_exception_handler(CoachAIException, coach_ai_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Inclui os roteadores das diferentes partes da aplicação
logger.info("Registering API routers")
app.include_router(users_router, prefix="/api/v1", tags=["Users"])
app.include_router(contests_router, prefix="/api/v1/contests", tags=["Contests"])
app.include_router(study_router, prefix="/api/v1/study", tags=["Study"])
app.include_router(guided_lesson_router, prefix="/api/v1/guided-lesson", tags=["Guided Lesson"])

# Healthcheck
@app.get("/health")
def health_check():
    logger.debug("Health check requested")
    return {"status": "ok"}

logger.info(
    "FastAPI application initialized successfully",
    environment=settings.ENVIRONMENT,
    log_level=settings.LOG_LEVEL,
    rate_limiting_enabled=USE_RATE_LIMIT
)
