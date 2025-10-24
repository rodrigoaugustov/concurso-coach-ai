# backend/app/core/exception_handlers.py

import logging
from datetime import datetime
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .exceptions import (
    CoachAIException,
    AuthenticationError,
    ValidationError as DomainValidationError,
    BusinessLogicError,
    AIProcessingError,
)

logger = logging.getLogger(__name__)


def get_status_code_for_exception(exc: CoachAIException) -> int:
    """Mapeia tipos de exceção para códigos HTTP apropriados"""
    if isinstance(exc, AuthenticationError):
        return 401
    elif isinstance(exc, DomainValidationError):
        return 400
    elif isinstance(exc, BusinessLogicError):
        return 422  # Unprocessable Entity
    elif isinstance(exc, AIProcessingError):
        return 503  # Service Unavailable
    else:
        return 500  # Internal Server Error


async def coach_ai_exception_handler(request: Request, exc: CoachAIException):
    """Handler para todas as exceções customizadas do CoachAI"""
    
    # Log estruturado do erro
    logger.error(
        "CoachAI Exception",
        extra={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "user_agent": request.headers.get("user-agent"),
        },
    )
    
    # Determina status code baseado no tipo de exceção
    status_code = get_status_code_for_exception(exc)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
            }
        },
    )


def get_user_friendly_validation_message(error: dict) -> str:
    """Converte erros técnicos do Pydantic em mensagens user-friendly"""
    error_type = error.get("type", "")
    
    if error_type in {"string_too_short", "string_too_long"}:
        return "Tamanho de texto inválido"
    elif error_type in {"missing", "value_error.missing"}:
        return "Campo obrigatório ausente"
    elif error_type in {"int_parsing", "int_type"}:
        return "Número inteiro inválido"
    elif error_type in {"float_parsing", "float_type"}:
        return "Número decimal inválido"
    elif error_type in {"bool_parsing", "bool_type"}:
        return "Valor booleano inválido"
    elif "email" in error_type.lower():
        return "Formato de email inválido"
    elif "url" in error_type.lower():
        return "Formato de URL inválido"
    else:
        return error.get("msg", "Valor inválido")


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler melhorado para erros de validação do Pydantic"""
    logger.warning(
        "Pydantic Validation Error",
        extra={
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    # Transforma erros técnicos do Pydantic em mensagens user-friendly
    user_friendly_errors = []
    for error in exc.errors():
        field_name = " > ".join(str(loc) for loc in error["loc"])
        user_friendly_errors.append({
            "field": field_name,
            "message": get_user_friendly_validation_message(error),
            "invalid_value": error.get("input")
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dados enviados contêm erros",
                "details": {"field_errors": user_friendly_errors},
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
            }
        },
    )
