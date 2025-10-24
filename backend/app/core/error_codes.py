# backend/app/core/error_codes.py

"""
Catálogo de códigos de erro para integração com frontend.
Este arquivo documenta todos os error_code disponíveis no sistema.
"""

ERROR_CODES = {
    # Genéricos
    "GENERIC_ERROR": "Erro genérico",
    
    # Autenticação
    "INVALID_CREDENTIALS": "Email ou senha inválidos",
    "TOKEN_EXPIRED": "Sessão expirada",
    
    # Validação
    "INVALID_FILE": "Arquivo inválido",
    "DUPLICATE_ENROLLMENT": "Inscrição duplicada",
    "VALIDATION_ERROR": "Erros de validação de dados",
    
    # IA e Processamento
    "GEMINI_API_ERROR": "Erro temporário no provedor de IA",
    "AI_VALIDATION_ERROR": "Resposta inválida da IA",
    "MAX_RETRIES_EXCEEDED": "Limite de tentativas excedido",
    
    # Regras de Negócio
    "EXAM_DATE_PASSED": "Prova já realizada",
    "NO_TOPICS_AVAILABLE": "Sem tópicos disponíveis"
}
