from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.database import engine
from app import models
from app.users.router import router as users_router
from app.contests.router import router as contests_router
from app.study.router import router as study_router
from app.study.sessions_router import router as sessions_router
from fastapi.middleware.cors import CORSMiddleware
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
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address)
    USE_RATE_LIMIT = True
    logger.info("Rate limiting enabled")
except Exception as e:
    limiter = None
    RateLimitExceeded = None
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
    "http://localhost:3000", # A origem do nosso frontend Next.js em desenvolvimento
]

logger.info("Configuring CORS middleware", allowed_origins=origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Permite as origens na lista
    allow_credentials=True, # Permite cookies (importante para o futuro)
    allow_methods=["*"],    # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"],    # Permite todos os cabeçalhos
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

# Global rate-limit handler (Solution A)
if USE_RATE_LIMIT and RateLimitExceeded is not None:
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        logger.warning(
            "Rate limit exceeded",
            endpoint=str(request.url),
            user_agent=request.headers.get("user-agent"),
            remote_addr=request.client.host if request.client else None
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": f"Rate limit exceeded: {exc.detail}"},
        )

# Inclui os roteadores das diferentes partes da aplicação
logger.info("Registering API routers")
app.include_router(users_router, prefix="/api/v1", tags=["Users"])
app.include_router(contests_router, prefix="/api/v1/contests", tags=["Contests"])
app.include_router(study_router, prefix="/api/v1/study", tags=["Study"])
app.include_router(sessions_router, tags=["Guided Learning Sessions"])  # Already has prefix

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