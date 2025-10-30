# backend/app/core/middleware.py

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import Response
from starlette.requests import Request
from typing import Callable

from .logging import get_logger, set_request_context, clear_request_context, generate_request_id
from .security import decode_token_optional

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # CSP básica; ajuste conforme front
    "Content-Security-Policy": "default-src 'self'; connect-src 'self' https://cdn.jsdelivr.net; font-src https://cdn.jsdelivr.net data:; img-src 'self' data: https://fastapi.tiangolo.com; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request, call_next: Callable):
        response: Response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            if k not in response.headers:
                response.headers[k] = v
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging estruturado de requisições HTTP."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("middleware.request")
        
        # Endpoints que não devem ser logados (health checks, metrics, etc.)
        self.skip_paths = {
            "/health",
            "/metrics",
            "/favicon.ico"
        }

    async def dispatch(self, request: Request, call_next: Callable):
        # Gera um ID único para esta requisição
        request_id = generate_request_id()
        
        # Tenta extrair user_id do token JWT se presente
        user_id = None
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_token_optional(token)
                if payload:
                    user_id = payload.get("sub")
        except Exception:
            # Se não conseguir decodificar o token, continua sem user_id
            pass
        
        # Define o contexto da requisição
        set_request_context(request_id, user_id)
        
        # Adiciona request_id nos headers da resposta para facilitar debugging
        start_time = time.time()
        
        # Skip logging para alguns endpoints
        skip_logging = request.url.path in self.skip_paths
        
        if not skip_logging:
            self.logger.info(
                "Request started",
                method=request.method,
                path=request.url.path,
                query_params=str(request.query_params) if request.query_params else None,
                user_agent=request.headers.get("user-agent"),
                client_ip=self._get_client_ip(request)
            )
        
        try:
            response = await call_next(request)
            
            # Adiciona o request_id no header da resposta
            response.headers["X-Request-ID"] = request_id
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            if not skip_logging:
                # Log de sucesso
                log_data = {
                    "Request completed": "",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
                
                # Classifica por nível baseado no status code
                if response.status_code >= 500:
                    self.logger.error("Server error response", **log_data)
                elif response.status_code >= 400:
                    self.logger.warning("Client error response", **log_data)
                elif duration_ms > 5000:  # Requests muito lentos
                    self.logger.warning("Slow request detected", **log_data)
                else:
                    self.logger.info("Request completed successfully", **log_data)
            
            return response
            
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            if not skip_logging:
                self.logger.error(
                    "Request failed with exception",
                    method=request.method,
                    path=request.url.path,
                    duration_ms=duration_ms,
                    error=str(exc),
                    error_type=type(exc).__name__
                )
            
            raise
        finally:
            # Limpa o contexto da requisição
            clear_request_context()
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrai o IP do cliente considerando proxies."""
        # Verifica headers comuns de proxy
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Pega o primeiro IP da lista (cliente real)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback para o IP da conexão direta
        if request.client:
            return request.client.host
            
        return "unknown"