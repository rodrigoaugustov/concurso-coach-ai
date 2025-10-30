"""
Configuração de logging estruturado usando structlog.

Este módulo configura um sistema de logging JSON estruturado que facilita:
- Debug em produção
- Monitoramento de performance
- Rastreamento de erros
- Auditoria de operações críticas (IA, processamento de editais)
"""

import logging
import logging.config
import sys
from typing import Optional
import uuid
from contextvars import ContextVar

import structlog
from structlog import stdlib

# Context variables para rastreamento de requisições
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


def set_request_context(request_id: str, user_id: Optional[str] = None) -> None:
    """Define o contexto da requisição atual para logs estruturados."""
    request_id_var.set(request_id)
    user_id_var.set(user_id)


def clear_request_context() -> None:
    """Limpa o contexto da requisição atual."""
    request_id_var.set(None)
    user_id_var.set(None)


def generate_request_id() -> str:
    """Gera um ID único para a requisição."""
    return f"req_{uuid.uuid4().hex[:8]}"


def add_request_context(logger, method_name, event_dict):
    """Processor que adiciona contexto da requisição aos logs."""
    # Validação de segurança para evitar tuple
    if not isinstance(event_dict, dict):
        return event_dict
        
    request_id = request_id_var.get()
    user_id = user_id_var.get()
    
    if request_id:
        event_dict['request_id'] = request_id
    if user_id:
        event_dict['user_id'] = user_id
        
    return event_dict


def add_severity_level(logger, method_name, event_dict):
    """Processor que padroniza o campo level para compatibilidade com Google Cloud Logging."""
    # Validação de segurança para evitar tuple
    if not isinstance(event_dict, dict):
        return event_dict
        
    level = event_dict.get('level')
    if level:
        # Mapeia níveis Python para Google Cloud Logging severity
        severity_map = {
            'debug': 'DEBUG',
            'info': 'INFO', 
            'warning': 'WARNING',
            'error': 'ERROR',
            'critical': 'CRITICAL'
        }
        event_dict['severity'] = severity_map.get(level.lower(), level.upper())
    
    return event_dict


def filter_sensitive_data(logger, method_name, event_dict):
    """Processor que remove dados sensíveis dos logs."""
    # Validação de segurança para evitar tuple
    if not isinstance(event_dict, dict):
        return event_dict
        
    sensitive_fields = ['password', 'token', 'api_key', 'secret']
    
    def clean_dict(data):
        if isinstance(data, dict):
            return {
                key: '[REDACTED]' if any(sens in key.lower() for sens in sensitive_fields) 
                else clean_dict(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [clean_dict(item) for item in data]
        return data
    
    return clean_dict(event_dict)


def setup_logging(log_level: str = "INFO", is_development: bool = True) -> None:
    """Configura o sistema de logging estruturado.
    
    Args:
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        is_development: Se True, logs são mais legíveis para desenvolvimento
    """
    
    # Configuração base do logging Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    
    # Pipeline simples e compatível - sem CallsiteParameterAdder para evitar problemas
    processors = [
        # Adiciona contexto da requisição
        add_request_context,
        # Adiciona severity level
        add_severity_level,
        # Remove dados sensíveis
        filter_sensitive_data,
        # Adiciona timestamp ISO 8601
        structlog.processors.TimeStamper(fmt="iso"),
        # Adiciona nome do logger
        structlog.stdlib.add_logger_name,
        # Adiciona nível do log
        structlog.stdlib.add_log_level,
        # Prepara args posicionais
        structlog.stdlib.PositionalArgumentsFormatter(),
    ]
    
    if is_development:
        # Em desenvolvimento: formato colorido e legível
        processors.extend([
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    else:
        # Em produção: formato JSON estruturado
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configuração para bibliotecas externas
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.INFO)
    logging.getLogger("google.cloud").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado configurado."""
    return structlog.get_logger(name)


# Logger padrão para o módulo core
logger = get_logger(__name__)


class LogContext:
    """Context manager para adicionar contexto temporário aos logs."""
    
    def __init__(self, **context):
        self.context = context
        self.logger = get_logger()
        
    def __enter__(self):
        return self.logger.bind(**self.context)
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def log_function_call(func_name: str, **kwargs):
    """Decorator para logar chamadas de função automaticamente."""
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            log = get_logger().bind(
                function=func_name,
                args_count=len(args),
                kwargs_count=len(func_kwargs),
                **kwargs
            )
            
            log.debug(f"Iniciando execução de {func_name}")
            try:
                result = func(*args, **func_kwargs)
                log.info(f"Execução de {func_name} concluída com sucesso")
                return result
            except Exception as e:
                log.error(
                    f"Erro na execução de {func_name}",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
                
        return wrapper
    return decorator