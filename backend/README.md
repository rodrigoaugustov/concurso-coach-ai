# backend/README.md (trecho adicionado ao final)

## Refatoração: Code Smells (Issue #21)

Este branch implementa a refatoração para reduzir God Classes, métodos longos e magic numbers.

- Constantes centralizadas: `app/core/constants.py`
- Validadores centralizados: `app/core/validators.py`
- Study pipeline decomposto:
  - `app/study/data_collector.py`
  - `app/study/topic_analyzer.py`
  - `app/study/plan_organizer.py`
  - `app/study/plan_persister.py`
  - Orquestrador: `app/study/plan_generator.py`
- Contests task delegada para `EdictProcessor`:
  - `app/contests/edict_processor.py`
  - Task Celery mantém assinatura e retry: `app/contests/tasks.py`

### Testes adicionados
- `tests/unit/test_core/test_constants.py`
- `tests/unit/test_core/test_validators.py`
- `tests/unit/test_study/test_plan_generator_equivalence.py`
- `tests/unit/test_study/test_validators_integration.py`
- `tests/unit/test_contests/test_edict_processor.py`
- `tests/unit/test_contests/test_tasks_delegation.py`
