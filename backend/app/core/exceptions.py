# backend/app/core/exceptions.py

class CoachAIException(Exception):
    """Base exception para todas as exceções customizadas do projeto"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or "GENERIC_ERROR"
        self.details = details or {}
        super().__init__(self.message)

# === EXCEÇÕES DE AUTENTICAÇÃO ===
class AuthenticationError(CoachAIException):
    """Erros relacionados à autenticação de usuários"""
    pass

class InvalidCredentialsError(AuthenticationError):
    def __init__(self):
        super().__init__(
            message="Email ou senha inválidos",
            error_code="INVALID_CREDENTIALS"
        )

class TokenExpiredError(AuthenticationError):
    def __init__(self):
        super().__init__(
            message="Sua sessão expirou. Faça login novamente",
            error_code="TOKEN_EXPIRED"
        )

# === EXCEÇÕES DE VALIDAÇÃO ===
class ValidationError(CoachAIException):
    """Erros de validação de dados de entrada"""
    pass

class InvalidFileError(ValidationError):
    def __init__(self, file_type: str, max_size_mb: int):
        super().__init__(
            message=f"Arquivo inválido. Apenas {file_type} de até {max_size_mb}MB são permitidos",
            error_code="INVALID_FILE",
            details={"allowed_type": file_type, "max_size_mb": max_size_mb}
        )

class DuplicateEnrollmentError(ValidationError):
    def __init__(self, role_name: str, contest_name: str):
        super().__init__(
            message=f"Você já está inscrito no cargo '{role_name}' do concurso '{contest_name}'",
            error_code="DUPLICATE_ENROLLMENT",
            details={"role_name": role_name, "contest_name": contest_name}
        )

# === EXCEÇÕES DE IA ===
class AIProcessingError(CoachAIException):
    """Erros relacionados ao processamento com IA"""
    pass

class GeminiAPIError(AIProcessingError):
    def __init__(self, api_error: str, retry_count: int = 0):
        super().__init__(
            message="Erro temporario no processamento. Tentando novamente...",
            error_code="GEMINI_API_ERROR",
            details={"api_error": api_error, "retry_count": retry_count}
        )

class AIValidationError(AIProcessingError):
    def __init__(self, validation_errors: list[str]):
        super().__init__(
            message="A IA gerou uma resposta inválida. Tentando corrigir...",
            error_code="AI_VALIDATION_ERROR",
            details={"validation_errors": validation_errors}
        )

class MaxRetriesExceededError(AIProcessingError):
    def __init__(self, operation: str, max_retries: int):
        super().__init__(
            message=f"Não foi possível completar {operation} após {max_retries} tentativas",
            error_code="MAX_RETRIES_EXCEEDED",
            details={"operation": operation, "max_retries": max_retries}
        )

# === EXCEÇÕES DE BUSINESS LOGIC ===
class BusinessLogicError(CoachAIException):
    """Erros de regras de negócio"""
    pass

class ExamDatePassedError(BusinessLogicError):
    def __init__(self, exam_date: str):
        super().__init__(
            message=f"Não é possível gerar plano de estudos. A prova foi em {exam_date}",
            error_code="EXAM_DATE_PASSED",
            details={"exam_date": exam_date}
        )

class NoTopicsAvailableError(BusinessLogicError):
    def __init__(self):
        super().__init__(
            message="Nenhum tópico disponível para gerar plano de estudos",
            error_code="NO_TOPICS_AVAILABLE"
        )
