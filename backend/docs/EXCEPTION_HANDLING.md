# Sistema de Exception Handling Customizado

Este documento descreve o sistema de tratamento de erro customizado implementado no Concurso Coach AI, conforme especificado na Issue #19.

## Visão Geral

O sistema implementa uma hierarquia de exceções customizadas com:
- Mensagens user-friendly para o frontend
- Códigos de erro padronizados
- Status HTTP apropriados
- Logs estruturados para observabilidade

## Hierarquia de Exceções

### Base: `CoachAIException`
Todas as exceções customizadas herdam da classe base:
```python
from app.core.exceptions import CoachAIException

raise CoachAIException(
    message="Mensagem para o usuário",
    error_code="CUSTOM_ERROR_CODE", 
    details={"extra": "informations"}
)
```

### Categorias de Erros

#### 1. Autenticação (`AuthenticationError`) - Status 401
- `InvalidCredentialsError`: Email/senha inválidos
- `TokenExpiredError`: Sessão expirada

#### 2. Validação (`ValidationError`) - Status 400
- `InvalidFileError`: Arquivo inválido (tipo/tamanho)
- `DuplicateEnrollmentError`: Inscrição duplicada

#### 3. IA (`AIProcessingError`) - Status 503
- `GeminiAPIError`: Erro na API da Google
- `AIValidationError`: Resposta inválida da IA
- `MaxRetriesExceededError`: Limite de tentativas excedido

#### 4. Regras de Negócio (`BusinessLogicError`) - Status 422
- `ExamDatePassedError`: Prova já realizada
- `NoTopicsAvailableError`: Sem tópicos disponíveis

## Uso no Código

### Substituindo Exceções Genéricas

**Antes:**
```python
raise HTTPException(status_code=400, detail="Invalid file")
```

**Depois:**
```python
from app.core.exceptions import InvalidFileError
raise InvalidFileError("PDF", 50)  # tipo, tamanho_max_mb
```

### Exemplo no Celery (contests/tasks.py)

**Antes:**
```python
raise ValueError("Inconsistência de tópicos após o refinamento da IA")
```

**Depois:**
```python
from app.core.exceptions import AIValidationError
raise AIValidationError([
    "IA removeu tópicos: {missing}",
    "IA inventou tópicos: {added}"
])
```

## Códigos de Erro

Todos os error codes estão catalogados em `app.core.error_codes.py` para integração com o frontend:

```python
ERROR_CODES = {
    "INVALID_CREDENTIALS": "Email ou senha inválidos",
    "TOKEN_EXPIRED": "Sessão expirada",
    "INVALID_FILE": "Arquivo inválido",
    "GEMINI_API_ERROR": "Erro temporário no provedor de IA",
    "EXAM_DATE_PASSED": "Prova já realizada",
    # ... outros códigos
}
```

## Formato de Resposta JSON

Todas as exceções retornam uma estrutura consistente:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email ou senha inválidos",
    "details": {},
    "timestamp": "2025-10-24T18:15:00Z",
    "path": "/api/v1/auth/login"
  }
}
```

### Erros de Validação (Pydantic)

Erros do Pydantic/FastAPI são convertidos para mensagens user-friendly:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dados enviados contêm erros",
    "details": {
      "field_errors": [
        {
          "field": "email",
          "message": "Formato de email inválido",
          "invalid_value": "not-an-email"
        }
      ]
    }
  }
}
```

## Configuração no FastAPI

Os handlers são registrados automaticamente em `main.py`:

```python
from app.core.exceptions import CoachAIException
from app.core.exception_handlers import (
    coach_ai_exception_handler,
    validation_exception_handler,
)

app.add_exception_handler(CoachAIException, coach_ai_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
```

## Logs Estruturados

Todas as exceções geram logs estruturados para observabilidade:

```python
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
```

## Testes

Todos os componentes estão cobertos por testes em `backend/tests/unit/test_core/test_exceptions.py`:

- Hierarquia de exceções
- Mapeamento de status HTTP
- Handlers de resposta
- Mensagens user-friendly
- Integração com FastAPI

Para rodar os testes:
```bash
uv run pytest backend/tests/unit/test_core/test_exceptions.py -v
```

## Benefícios

### Para Usuários
- Mensagens de erro claras e acionáveis
- Status codes HTTP apropriados
- Consistência na estrutura de responses

### Para Desenvolvedores
- Fácil identificação de tipos de erro
- Logs estruturados com contexto
- Debugging simplificado
- Testes abrangentes

### Para Observabilidade
- Error codes padronizados para métricas
- Logs com detalhes suficientes para análise
- Rastreabilidade de erros

## Integração Frontend

O frontend pode usar os `error_code` para:

```typescript
if (error.code === 'INVALID_CREDENTIALS') {
  // Mostrar formulário de login
} else if (error.code === 'TOKEN_EXPIRED') {
  // Redirecionar para login
} else if (error.code === 'GEMINI_API_ERROR') {
  // Mostrar mensagem de "tente novamente"
}
```

## Diretrizes de Desenvolvimento

1. **Sempre use exceções customizadas** ao invés de `HTTPException` genéricas
2. **Escolha a categoria apropriada** (Auth, Validation, AI, Business)
3. **Forneça contexto nos `details`** quando útil
4. **Teste o mapeamento de status** ao adicionar novas exceções
5. **Documente novos error codes** em `error_codes.py`

## Exemplos de Uso por Módulo

### Users (autenticação)
```python
from app.core.exceptions import InvalidCredentialsError, TokenExpiredError

if not verify_password(password, user.password_hash):
    raise InvalidCredentialsError()

if token_expired(token):
    raise TokenExpiredError()
```

### Contests (upload e validação)
```python
from app.core.exceptions import InvalidFileError, DuplicateEnrollmentError

if file.content_type != "application/pdf":
    raise InvalidFileError("PDF", 50)

if existing_enrollment:
    raise DuplicateEnrollmentError(role.name, contest.name)
```

### Study (regras de negócio)
```python
from app.core.exceptions import ExamDatePassedError, NoTopicsAvailableError

if contest.exam_date < datetime.now().date():
    raise ExamDatePassedError(contest.exam_date.isoformat())

if not available_topics:
    raise NoTopicsAvailableError()
```
