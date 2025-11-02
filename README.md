# 🎯 Concurso Coach AI

Uma plataforma inteligente de preparação para concursos públicos, utilizando Inteligência Artificial para personalizar o estudo e otimizar o aprendizado.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Como Desenvolver](#como-desenvolver)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Padrões de Desenvolvimento](#padrões-de-desenvolvimento)
- [Como Contribuir](#como-contribuir)
- [Troubleshooting](#troubleshooting)

## 🎯 Visão Geral

O Concurso Coach AI é uma aplicação full-stack que combina:

- **Backend**: API REST em FastAPI com autenticação, processamento assíncrono e integração com IA
- **Frontend**: Interface moderna em Next.js com TypeScript e Tailwind CSS
- **Banco de Dados**: PostgreSQL para persistência de dados
- **Cache/Filas**: Redis para cache e processamento assíncrono com Celery
- **IA**: Integração com modelos de linguagem para personalização do ensino

### Principais Funcionalidades

- Sistema de autenticação e perfis de usuário
- Análise personalizada de editais de concursos
- Geração de planos de estudo adaptativos
- Acompanhamento de progresso e métricas
- Interface intuitiva e responsiva

## 🏗️ Arquitetura

```
concurso-coach-ai/
├── backend/          # API FastAPI + Celery Worker
├── frontend/         # Next.js + TypeScript + Tailwind
├── docker-compose.yml # Orquestração de todos os serviços
└── docs/             # Documentação adicional
```

### Serviços (Docker Compose)

- **Backend** (FastAPI): `localhost:8000`
- **Frontend** (Next.js): `localhost:3000`
- **Database** (PostgreSQL): `localhost:5432`
- **Cache** (Redis): Interno
- **Admin DB** (Adminer): `localhost:8080`
- **Task Monitor** (Flower): `localhost:5555`

## ⚙️ Configuração do Ambiente

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)
- Editor de código (recomendado: VS Code)

### Configuração Inicial

1. **Clone o repositório**
   ```bash
   git clone https://github.com/rodrigoaugustov/concurso-coach-ai.git
   cd concurso-coach-ai
   ```

2. **Configure as variáveis de ambiente**
   ```bash
   cp .env.example .env
   ```
   
   Edite o arquivo `.env` com suas configurações:
   ```env
   # Database
   POSTGRES_USER=concurso_user
   POSTGRES_PASSWORD=concurso_password
   POSTGRES_DB=concurso_coach_ai
   DATABASE_URL=postgresql://concurso_user:concurso_password@db:5432/concurso_coach_ai
   
   # Security
   SECRET_KEY=sua-chave-secreta-super-segura-aqui
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   
   # Redis
   REDIS_URL=redis://redis:6379/0
   
   # AI Services (configure conforme necessário)
   OPENAI_API_KEY=sua-chave-openai
   GOOGLE_API_KEY=sua-chave-google
   ```

3. **Inicie todos os serviços**
   ```bash
   docker-compose up -d
   ```

4. **Verifique se tudo está funcionando**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs
   - Admin DB: http://localhost:8080
   - Task Monitor: http://localhost:5555

## 🚀 Como Desenvolver

### Workflow de Desenvolvimento

1. **Crie uma branch para sua feature**
   ```bash
   git checkout -b feature/nome-da-sua-feature
   ```

2. **Desenvolvimento com Hot Reload**
   ```bash
   # Inicia todos os serviços com hot reload ativo
   docker-compose up
   ```
   
   - **Backend**: Mudanças em `backend/app/` são refletidas automaticamente
   - **Frontend**: Mudanças em `frontend/src/` são refletidas automaticamente

3. **Testando suas mudanças**
   ```bash
   # Backend - Execute testes
   docker-compose exec backend python -m pytest
   
   # Frontend - Verifique linting
   docker-compose exec frontend npm run lint
   ```

4. **Commit e Push**
   ```bash
   git add .
   git commit -m "feat: adiciona nova funcionalidade X"
   git push origin feature/nome-da-sua-feature
   ```

5. **Abra um Pull Request**

### Comandos Úteis

```bash
# Ver logs em tempo real
docker-compose logs -f backend
docker-compose logs -f frontend

# Executar comandos dentro dos containers
docker-compose exec backend python manage.py migrate
docker-compose exec backend python -c "from app.core.database import engine; print('DB Connected!')"
docker-compose exec frontend npm install nova-dependencia

# Reiniciar um serviço específico
docker-compose restart backend
docker-compose restart frontend

# Parar tudo
docker-compose down

# Limpar dados do banco (cuidado!)
docker-compose down -v
```

## 📁 Estrutura do Projeto

### Backend (`/backend`)

```
backend/
├── app/
│   ├── core/          # Configurações, database, autenticação
│   ├── users/         # Módulo de usuários
│   ├── contests/      # Módulo de concursos
│   ├── study/         # Módulo de estudos e IA
│   ├── main.py        # Aplicação FastAPI principal
│   └── models.py      # Modelos base
├── tests/             # Testes automatizados
├── docs/              # Documentação específica do backend
├── Dockerfile
└── pyproject.toml     # Dependências Python
```

**Principais dependências:**
- FastAPI, SQLAlchemy, Pydantic
- Celery, Redis
- LangChain (para IA)
- Google Cloud Storage

### Frontend (`/frontend`)

```
frontend/
├── src/
│   ├── app/           # App Router do Next.js
│   ├── components/    # Componentes reutilizáveis
│   ├── lib/           # Utilitários e configurações
│   └── types/         # Tipos TypeScript
├── public/            # Assets estáticos
├── Dockerfile
└── package.json
```

**Principais dependências:**
- Next.js 14, React 18, TypeScript
- Tailwind CSS, Heroicons
- Class Variance Authority (para componentes)

## 📐 Padrões de Desenvolvimento

### Backend (FastAPI)

1. **Estrutura modular**: Cada feature tem seu próprio diretório com models, routes, services
2. **Dependency Injection**: Use FastAPI dependencies para autenticação, database
3. **Async/await**: Prefira funções assíncronas quando possível
4. **Type hints**: Sempre use type hints em Python
5. **Pydantic models**: Para validação de dados de entrada e saída

**Exemplo de estrutura de módulo:**
```python
# app/users/models.py
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)

# app/users/schemas.py  
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# app/users/routes.py
@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    return await user_service.create_user(db, user)
```

### Frontend (Next.js)

1. **App Router**: Use o App Router do Next.js 14
2. **TypeScript**: Sempre tipado, evite `any`
3. **Componentes funcionais**: Use hooks em vez de class components
4. **Tailwind CSS**: Para estilização, evite CSS inline
5. **Componentização**: Crie componentes reutilizáveis

**Exemplo de componente:**
```tsx
// src/components/ui/Button.tsx
interface ButtonProps {
  variant?: 'default' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
  onClick?: () => void
}

export function Button({ variant = 'default', size = 'md', children, onClick }: ButtonProps) {
  return (
    <button
      className={cn(
        "rounded-md font-medium transition-colors",
        variant === 'default' && "bg-blue-600 text-white hover:bg-blue-700",
        variant === 'outline' && "border border-gray-300 hover:bg-gray-50",
        size === 'sm' && "px-3 py-1.5 text-sm",
        size === 'md' && "px-4 py-2",
        size === 'lg' && "px-6 py-3 text-lg"
      )}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
```

### Padrões de Commit

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: adiciona nova funcionalidade
fix: corrige bug específico
docs: atualiza documentação
style: mudanças de formatação
refactor: refatoração sem mudança de funcionalidade
test: adiciona ou modifica testes
chore: mudanças de build, dependências, etc.
```

## 🤝 Como Contribuir

### 1. Entendendo o Kanban

O projeto usa um board Kanban no GitHub Projects. As issues são organizadas em:

- **Backlog**: Novas ideias e funcionalidades
- **To Do**: Pronto para desenvolvimento
- **In Progress**: Em desenvolvimento
- **Review**: Aguardando code review
- **Done**: Concluído

### 2. Escolhendo uma Issue

1. Vá para a aba **Issues** do repositório
2. Filtre por labels como `good-first-issue`, `help-wanted`
3. Escolha uma issue que faça sentido com seu nível de experiência
4. Comente na issue que você vai trabalhar nela

### 3. Desenvolvendo

1. Faça fork do repositório (se não for colaborador direto)
2. Crie uma branch: `git checkout -b issue-123-nova-feature`
3. Desenvolva seguindo os padrões acima
4. Teste localmente
5. Faça commit e push
6. Abra um Pull Request

### 4. Code Review

- PRs precisam de pelo menos 1 aprovação
- Mantenha PRs pequenos e focados
- Descreva claramente o que foi implementado
- Inclua screenshots para mudanças de UI
- Responda aos comentários construtivamente

### 5. Labels importantes

- `bug`: Correção de bugs
- `enhancement`: Melhorias
- `feature`: Novas funcionalidades
- `good-first-issue`: Ideal para iniciantes
- `help-wanted`: Precisamos de ajuda
- `priority-high`: Alta prioridade
- `backend`: Relacionado ao backend
- `frontend`: Relacionado ao frontend

## 🔧 Troubleshooting

### Problemas Comuns

**1. Erro de permissão no Docker**
```bash
# Linux/Mac
sudo docker-compose up

# Ou adicione seu usuário ao grupo docker
sudo usermod -aG docker $USER
# Depois faça logout/login
```

**2. Porta já em uso**
```bash
# Verificar o que está usando a porta
lsof -i :3000  # ou :8000, :5432, etc.

# Matar processo
kill -9 PID_DO_PROCESSO
```

**3. Banco de dados não conecta**
```bash
# Verificar se o container está rodando
docker-compose ps

# Ver logs do banco
docker-compose logs db

# Resetar o banco (CUIDADO: apaga dados!)
docker-compose down -v
docker-compose up -d
```

**4. Hot reload não funciona no Windows**
```yaml
# No docker-compose.yml, adicionar ao frontend:
environment:
  - CHOKIDAR_USEPOLLING=true
```

**5. Problemas com dependências Python**
```bash
# Rebuild do container backend
docker-compose build backend
docker-compose up -d backend
```

**6. Problemas com dependências Node.js**
```bash
# Limpar node_modules e reinstalar
docker-compose exec frontend rm -rf node_modules
docker-compose exec frontend npm install
```

### Onde Buscar Ajuda

1. **Issues do GitHub**: Para bugs e dúvidas específicas
2. **Documentação**: Verifique a pasta `/docs` e READMEs específicos
3. **Code Review**: Outros colaboradores podem ajudar nos PRs
4. **Logs**: Sempre verifique os logs quando algo não funcionar

---

## 🎉 Pronto para Contribuir!

Agora você tem tudo que precisa para contribuir com o projeto. Algumas dicas finais:

- **Comece pequeno**: Escolha issues simples para se familiarizar
- **Pergunte**: Não hesite em fazer perguntas nas issues
- **Seja consistente**: Siga os padrões estabelecidos
- **Teste bem**: Sempre teste suas mudanças localmente
- **Tenha paciência**: Code review é um processo colaborativo

Bem-vindo ao time! 🚀

---

**Links Úteis:**
- [Documentação FastAPI](https://fastapi.tiangolo.com/)
- [Documentação Next.js](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Docker Compose](https://docs.docker.com/compose/)