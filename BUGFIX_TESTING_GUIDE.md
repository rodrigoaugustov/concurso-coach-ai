# 🐛 **Guia de Testes - Correção Bug #1: Inscrição Duplicada**

## 📝 **Resumo da Correção**

Este guia documenta como testar a correção do **Issue #1** - bug que permitia inscrições duplicadas em cargos de concursos.

### **Problema Original:**
- Usuários conseguiam se inscrever múltiplas vezes no mesmo cargo
- Frontend mostrava todos os cargos disponíveis (incluindo já inscritos)
- Backend não validava inscrições duplicadas

### **Solução Implementada:**
- ✅ Validação no backend que impede inscrições duplicadas (retorna 409 Conflict)
- ✅ Novo endpoint para listar apenas cargos disponíveis para inscrição
- ✅ Mensagens de erro mais claras e informativas
- ✅ Testes automatizados completos

---

## 🚀 **Como Testar Manualmente**

### **Pré-requisitos:**
1. Backend rodando em `http://localhost:8000`
2. Usuário autenticado (token JWT válido)
3. Concursos processados na base de dados

### **Cenários de Teste:**

#### **1. Teste de Primeira Inscrição (Deve Funcionar)**
```bash
# 1. Liste os cargos disponíveis para o usuário
curl -X GET "http://localhost:8000/api/v1/study/available-roles" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -H "Content-Type: application/json"

# Resposta esperada: Lista de cargos disponíveis
# Status Code: 200
```

```bash
# 2. Inscreva-se em um cargo (use um role_id da resposta anterior)
curl -X POST "http://localhost:8000/api/v1/study/subscribe/1" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -H "Content-Type: application/json"

# Resposta esperada: Dados da inscrição criada
# Status Code: 201
```

#### **2. Teste de Inscrição Duplicada (Deve Falhar com 409)**
```bash
# Tente se inscrever novamente no mesmo cargo
curl -X POST "http://localhost:8000/api/v1/study/subscribe/1" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -H "Content-Type: application/json"

# Resposta esperada:
# Status Code: 409 Conflict
# Body: {"detail": "Usuário já está inscrito no cargo 'Nome do Cargo' deste concurso..."}
```

#### **3. Teste de Filtragem de Cargos Disponíveis**
```bash
# Liste novamente os cargos disponíveis
curl -X GET "http://localhost:8000/api/v1/study/available-roles" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -H "Content-Type: application/json"

# Resposta esperada: Lista SEM o cargo recém inscrito
# O cargo do passo 1 não deve aparecer mais
```

#### **4. Teste de Listagem de Inscrições do Usuário**
```bash
# Liste as inscrições ativas do usuário
curl -X GET "http://localhost:8000/api/v1/study/subscriptions" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -H "Content-Type: application/json"

# Resposta esperada: Lista com a inscrição do passo 1
# Status Code: 200
```

#### **5. Teste de Cargo Inexistente (Deve Falhar com 404)**
```bash
# Tente se inscrever em um cargo que não existe
curl -X POST "http://localhost:8000/api/v1/study/subscribe/99999" \
  -H "Authorization: Bearer SEU_TOKEN_JWT" \
  -H "Content-Type: application/json"

# Resposta esperada:
# Status Code: 404 Not Found
# Body: {"detail": "Role not found"}
```

---

## 🧪 **Executar Testes Automatizados**

```bash
# Navegar para o diretório do backend
cd backend/

# Executar os testes específicos da correção
pytest tests/test_enrollment_bug_fix.py -v

# Executar todos os testes
pytest tests/ -v
```

### **Testes Implementados:**
- ✅ `test_first_enrollment_success` - Primeira inscrição funciona
- ✅ `test_duplicate_enrollment_raises_409` - Duplicata retorna 409
- ✅ `test_enrollment_in_different_roles_allowed` - Cargos diferentes permitidos
- ✅ `test_nonexistent_role_raises_404` - Cargo inexistente retorna 404
- ✅ `test_all_roles_available_for_new_user` - Usuário novo vê todos os cargos
- ✅ `test_enrolled_roles_excluded_from_available` - Cargos inscritos são filtrados
- ✅ `test_multiple_enrollments_reduce_available_roles` - Filtragem progressiva
- ✅ `test_complete_enrollment_workflow` - Fluxo completo de inscrição

---

## 📊 **Endpoints Afetados pela Correção**

### **Novos Endpoints:**

| Método | Endpoint | Descrição | Status Codes |
|--------|----------|-----------|-------------|
| `GET` | `/api/v1/study/available-roles` | Lista cargos disponíveis para inscrição | 200 |
| `GET` | `/api/v1/study/subscriptions` | Lista inscrições do usuário | 200 |

### **Endpoints Modificados:**

| Método | Endpoint | Mudança | Status Codes |
|--------|----------|---------|-------------|
| `POST` | `/api/v1/study/subscribe/{role_id}` | Agora valida duplicatas | 201, 409, 404 |

### **Endpoints Não Afetados (mas relevantes para o fluxo):**

| Método | Endpoint | Uso |
|--------|----------|-----|
| `GET` | `/api/v1/contests/` | Lista todos os concursos (não filtra por usuário) |
| `GET` | `/api/v1/study/user-contests/` | Lista inscrições (mesmo que `/subscriptions`) |

---

## 🔍 **Validações Implementadas**

### **Backend (services.py):**
1. **Validação de Duplicata:** Verifica se `UserContest` já existe antes de criar
2. **Mensagem Clara:** Retorna nome do cargo na mensagem de erro
3. **Filtragem Inteligente:** `get_available_roles_for_user()` exclui cargos já inscritos
4. **Consulta Otimizada:** Usa subconsulta para performance em bases grandes

### **API (router.py):**
1. **Documentação OpenAPI:** Endpoints documentam possíveis erros (409, 404)
2. **Responses Padronizadas:** Seguem convenções HTTP corretas
3. **Segurança:** Todos endpoints são protegidos por autenticação

---

## ⚡ **Como Obter Token JWT para Testes**

```bash
# 1. Fazer login
curl -X POST "http://localhost:8000/api/v1/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=seu_email@teste.com&password=sua_senha"

# 2. Usar o access_token retornado nos headers Authorization
# Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🎯 **Critérios de Sucesso**

- [x] ❌ **Antes:** Usuário conseguia se inscrever múltiplas vezes no mesmo cargo
- [x] ✅ **Depois:** Segunda tentativa retorna erro 409 com mensagem clara

- [x] ❌ **Antes:** Frontend mostrava todos os cargos (incluindo já inscritos)
- [x] ✅ **Depois:** Endpoint `/available-roles` filtra cargos já inscritos

- [x] ❌ **Antes:** Sem validação de integridade no backend
- [x] ✅ **Depois:** Validação robusta com testes automatizados

---

## 📝 **Próximos Passos (Pós-Merge)**

1. **Frontend:** Atualizar `/onboarding/start` para usar `/available-roles`
2. **Frontend:** Implementar tratamento de erro 409 com UX amigável
3. **Database:** Considerar constraint UNIQUE em `UserContest(user_id, contest_role_id)`
4. **Monitoring:** Adicionar logs para tentativas de inscrição duplicada

---

**Status:** ✅ **Correção Completa e Testada**  
**Issue:** #1  
**Branch:** `bugfix/duplicate-enrollment-issue-1`