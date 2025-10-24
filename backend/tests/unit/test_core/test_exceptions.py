# backend/tests/unit/test_core/test_exceptions.py

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import (
    CoachAIException,
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    ValidationError as DomainValidationError,
    InvalidFileError,
    DuplicateEnrollmentError,
    AIProcessingError,
    AIValidationError,
    GeminiAPIError,
    MaxRetriesExceededError,
    BusinessLogicError,
    ExamDatePassedError,
    NoTopicsAvailableError,
)
from app.core.exception_handlers import (
    coach_ai_exception_handler,
    validation_exception_handler,
    get_status_code_for_exception,
    get_user_friendly_validation_message,
)


class TestExceptionHierarchy:
    """Testa a hierarquia de exceções customizadas"""
    
    def test_base_exception_properties(self):
        """Testa propriedades básicas da exceção base"""
        exc = CoachAIException("Test message", "TEST_CODE", {"key": "value"})
        assert exc.message == "Test message"
        assert exc.error_code == "TEST_CODE"
        assert exc.details == {"key": "value"}
        assert str(exc) == "Test message"
    
    def test_base_exception_defaults(self):
        """Testa valores padrão da exceção base"""
        exc = CoachAIException("Test message")
        assert exc.message == "Test message"
        assert exc.error_code == "GENERIC_ERROR"
        assert exc.details == {}
    
    def test_authentication_error_hierarchy(self):
        """Testa hierarquia de erros de autenticação"""
        exc = InvalidCredentialsError()
        assert isinstance(exc, AuthenticationError)
        assert isinstance(exc, CoachAIException)
        assert exc.error_code == "INVALID_CREDENTIALS"
        assert "Email ou senha inválidos" in exc.message
        
        token_exc = TokenExpiredError()
        assert isinstance(token_exc, AuthenticationError)
        assert token_exc.error_code == "TOKEN_EXPIRED"
        assert "sessão expirou" in token_exc.message
    
    def test_validation_error_hierarchy(self):
        """Testa hierarquia de erros de validação"""
        file_exc = InvalidFileError("PDF", 10)
        assert isinstance(file_exc, DomainValidationError)
        assert isinstance(file_exc, CoachAIException)
        assert file_exc.error_code == "INVALID_FILE"
        assert file_exc.details["allowed_type"] == "PDF"
        assert file_exc.details["max_size_mb"] == 10
        
        dup_exc = DuplicateEnrollmentError("Analista", "SEAP 2025")
        assert isinstance(dup_exc, DomainValidationError)
        assert dup_exc.error_code == "DUPLICATE_ENROLLMENT"
        assert dup_exc.details["role_name"] == "Analista"
        assert dup_exc.details["contest_name"] == "SEAP 2025"
    
    def test_ai_processing_error_hierarchy(self):
        """Testa hierarquia de erros de IA"""
        gemini_exc = GeminiAPIError("Rate limit exceeded", 2)
        assert isinstance(gemini_exc, AIProcessingError)
        assert isinstance(gemini_exc, CoachAIException)
        assert gemini_exc.error_code == "GEMINI_API_ERROR"
        assert gemini_exc.details["api_error"] == "Rate limit exceeded"
        assert gemini_exc.details["retry_count"] == 2
        
        validation_exc = AIValidationError(["Missing field", "Invalid format"])
        assert isinstance(validation_exc, AIProcessingError)
        assert validation_exc.error_code == "AI_VALIDATION_ERROR"
        assert validation_exc.details["validation_errors"] == ["Missing field", "Invalid format"]
        
        retry_exc = MaxRetriesExceededError("PDF extraction", 3)
        assert isinstance(retry_exc, AIProcessingError)
        assert retry_exc.error_code == "MAX_RETRIES_EXCEEDED"
        assert retry_exc.details["operation"] == "PDF extraction"
        assert retry_exc.details["max_retries"] == 3
    
    def test_business_logic_error_hierarchy(self):
        """Testa hierarquia de erros de regras de negócio"""
        exam_exc = ExamDatePassedError("2024-12-01")
        assert isinstance(exam_exc, BusinessLogicError)
        assert isinstance(exam_exc, CoachAIException)
        assert exam_exc.error_code == "EXAM_DATE_PASSED"
        assert exam_exc.details["exam_date"] == "2024-12-01"
        
        topics_exc = NoTopicsAvailableError()
        assert isinstance(topics_exc, BusinessLogicError)
        assert topics_exc.error_code == "NO_TOPICS_AVAILABLE"


class TestStatusCodeMapping:
    """Testa o mapeamento de exceções para códigos HTTP"""
    
    def test_authentication_error_status(self):
        """Testa status 401 para erros de autenticação"""
        assert get_status_code_for_exception(InvalidCredentialsError()) == 401
        assert get_status_code_for_exception(TokenExpiredError()) == 401
    
    def test_validation_error_status(self):
        """Testa status 400 para erros de validação"""
        assert get_status_code_for_exception(InvalidFileError("PDF", 10)) == 400
        assert get_status_code_for_exception(DuplicateEnrollmentError("role", "contest")) == 400
    
    def test_business_logic_error_status(self):
        """Testa status 422 para erros de regras de negócio"""
        assert get_status_code_for_exception(ExamDatePassedError("2024-12-01")) == 422
        assert get_status_code_for_exception(NoTopicsAvailableError()) == 422
    
    def test_ai_processing_error_status(self):
        """Testa status 503 para erros de IA"""
        assert get_status_code_for_exception(GeminiAPIError("error", 0)) == 503
        assert get_status_code_for_exception(AIValidationError(["error"])) == 503
        assert get_status_code_for_exception(MaxRetriesExceededError("op", 3)) == 503
    
    def test_generic_error_status(self):
        """Testa status 500 para erro genérico"""
        generic_exc = CoachAIException("Generic error")
        assert get_status_code_for_exception(generic_exc) == 500


class TestValidationMessageMapping:
    """Testa a conversão de mensagens de validação do Pydantic"""
    
    def test_string_validation_messages(self):
        """Testa mensagens para erros de string"""
        assert get_user_friendly_validation_message({"type": "string_too_short"}) == "Tamanho de texto inválido"
        assert get_user_friendly_validation_message({"type": "string_too_long"}) == "Tamanho de texto inválido"
    
    def test_missing_field_messages(self):
        """Testa mensagens para campos obrigatórios"""
        assert get_user_friendly_validation_message({"type": "missing"}) == "Campo obrigatório ausente"
        assert get_user_friendly_validation_message({"type": "value_error.missing"}) == "Campo obrigatório ausente"
    
    def test_number_validation_messages(self):
        """Testa mensagens para erros de número"""
        assert get_user_friendly_validation_message({"type": "int_parsing"}) == "Número inteiro inválido"
        assert get_user_friendly_validation_message({"type": "float_type"}) == "Número decimal inválido"
    
    def test_boolean_validation_messages(self):
        """Testa mensagens para erros de booleano"""
        assert get_user_friendly_validation_message({"type": "bool_parsing"}) == "Valor booleano inválido"
    
    def test_email_url_validation_messages(self):
        """Testa mensagens para email e URL"""
        assert get_user_friendly_validation_message({"type": "value_error.email"}) == "Formato de email inválido"
        assert get_user_friendly_validation_message({"type": "value_error.url"}) == "Formato de URL inválido"
    
    def test_fallback_message(self):
        """Testa mensagem de fallback para erros desconhecidos"""
        assert get_user_friendly_validation_message({"type": "unknown", "msg": "Custom message"}) == "Custom message"
        assert get_user_friendly_validation_message({"type": "unknown"}) == "Valor inválido"


@pytest.mark.asyncio
class TestExceptionHandlers:
    """Testa os handlers de exceções"""
    
    async def test_coach_ai_exception_handler_response_format(self):
        """Testa o formato da resposta do handler de exceções customizadas"""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.method = "POST"
        mock_request.headers.get.return_value = "test-agent"
        
        exc = InvalidCredentialsError()
        
        with patch('app.core.exception_handlers.logger') as mock_logger:
            response = await coach_ai_exception_handler(mock_request, exc)
        
        # Verifica estrutura da resposta
        assert response.status_code == 401
        content = response.body.decode()
        import json
        response_data = json.loads(content)
        
        assert "error" in response_data
        error = response_data["error"]
        assert error["code"] == "INVALID_CREDENTIALS"
        assert "Email ou senha inválidos" in error["message"]
        assert error["path"] == "/api/test"
        assert "timestamp" in error
        assert error["details"] == {}
        
        # Verifica se o log foi chamado
        mock_logger.error.assert_called_once()
    
    async def test_validation_exception_handler_response_format(self):
        """Testa o formato da resposta do handler de validação"""
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/users"
        mock_request.method = "POST"
        
        # Simula erros do Pydantic
        mock_exc = Mock(spec=RequestValidationError)
        mock_exc.errors.return_value = [
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "missing",
                "input": {"name": "test"}
            },
            {
                "loc": ("body", "age"),
                "msg": "value is not a valid integer",
                "type": "int_parsing",
                "input": "not_a_number"
            }
        ]
        
        with patch('app.core.exception_handlers.logger') as mock_logger:
            response = await validation_exception_handler(mock_request, mock_exc)
        
        # Verifica estrutura da resposta
        assert response.status_code == 422
        content = response.body.decode()
        import json
        response_data = json.loads(content)
        
        assert "error" in response_data
        error = response_data["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert error["message"] == "Dados enviados contêm erros"
        assert "field_errors" in error["details"]
        
        field_errors = error["details"]["field_errors"]
        assert len(field_errors) == 2
        
        # Verifica primeiro erro
        email_error = field_errors[0]
        assert email_error["field"] == "body > email"
        assert email_error["message"] == "Campo obrigatório ausente"
        
        # Verifica segundo erro
        age_error = field_errors[1]
        assert age_error["field"] == "body > age"
        assert age_error["message"] == "Número inteiro inválido"
        
        # Verifica se o log foi chamado
        mock_logger.warning.assert_called_once()


def test_integration_with_fastapi():
    """Testa integração com FastAPI usando TestClient"""
    app = FastAPI()
    app.add_exception_handler(CoachAIException, coach_ai_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    @app.get("/test-auth-error")
    def test_auth_error():
        raise InvalidCredentialsError()
    
    @app.get("/test-business-error")
    def test_business_error():
        raise ExamDatePassedError("2024-01-01")
    
    @app.post("/test-validation")
    def test_validation(item_id: int, name: str):
        return {"item_id": item_id, "name": name}
    
    client = TestClient(app)
    
    # Testa erro de autenticação
    response = client.get("/test-auth-error")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"
    
    # Testa erro de regra de negócio
    response = client.get("/test-business-error")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "EXAM_DATE_PASSED"
    
    # Força erro de validação (item_id deve ser int)
    response = client.post("/test-validation?item_id=not_an_int&name=test")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "field_errors" in data["error"]["details"]
