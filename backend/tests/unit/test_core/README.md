# Guia rápido para executar os testes do módulo core

Como executar
- Na raiz do backend, execute:
  - pytest
  - ou pytest -q --cov=app/core --cov-report=term-missing

Escopo coberto
- LangChainService
  - Inicialização (inclui provider inválido)
  - generate_structured_output (sucesso/erro)
  - generate_structured_output_from_content (sucesso/erro)
  - invoke_with_history (sucesso/erro)
- Database
  - engine importado
  - get_db: fornece sessão e garante fechamento
- Settings
  - Carregamento com variáveis mínimas
  - Defaults e validação de obrigatórios

Dependências
- pytest, pytest-mock, pytest-cov (configuradas via pyproject)

Observações
- Testes não fazem chamadas externas reais (IA/DB), tudo mockado
- Cobertura mínima-alvo: 80% no pacote app/core
