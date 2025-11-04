# Railway Deployment Guide

## Overview
Este documento descreve como fazer o deploy do Concurso Coach AI no Railway mantendo compatibilidade com desenvolvimento local.

## Arquitetura no Railway

### Serviços Criados:
1. **Backend (FastAPI)** - Porta 8000
2. **Frontend (Next.js)** - Porta 3000  
3. **PostgreSQL Database** - Gerenciado pelo Railway
4. **Redis** - Gerenciado pelo Railway
5. **Worker (Celery)** - Background tasks

## Variáveis de Ambiente no Railway

### Backend Service:
```bash
# Database (Railway fornece automaticamente)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (Railway fornece automaticamente)
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}/0
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/0

# JWT Secret (IMPORTANTE: Use valor seguro em produção)
JWT_SECRET_KEY="gere_uma_chave_segura_aqui"

# Google Cloud
GCS_BUCKET_NAME="coach-concursos-editais-bucket"
GCP_PROJECT_ID="concurso-coach-ai-app"
GOOGLE_CLOUD_PROJECT="concurso-coach-ai-app"
GEMINI_API_KEY="sua_gemini_api_key"

# LangSmith (opcional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY="sua_langchain_api_key"
LANGCHAIN_PROJECT=CoachConcursos

# Railway automaticamente define:
# PORT=8000
# RAILWAY_STATIC_URL
```

### Frontend Service:
```bash
# API URL (Railway conecta automaticamente)
NEXT_PUBLIC_API_URL=https://${{backend.RAILWAY_STATIC_URL}}/api/v1

# Railway automaticamente define:
# PORT=3000
# RAILWAY_STATIC_URL
```

### Worker Service (Celery):
```bash
# Same as backend, mas sem PORT
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}/0
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/0
GEMINI_API_KEY="sua_gemini_api_key"
GCS_BUCKET_NAME="coach-concursos-editais-bucket"
GCP_PROJECT_ID="concurso-coach-ai-app"
GOOGLE_CLOUD_PROJECT="concurso-coach-ai-app"
```

## Deploy Steps

### 1. Conectar Repositório
1. Faça login no [railway.app](https://railway.app)
2. Clique em "New Project"
3. Selecione "Deploy from GitHub repo"
4. Escolha `concurso-coach-ai` repository
5. Selecione a branch `railway-deployment`

### 2. Configurar Serviços
O Railway detectará automaticamente:
- `backend/Dockerfile` → Backend service
- `frontend/Dockerfile` → Frontend service

### 3. Adicionar Database
1. Clique em "Add Service" → "Database" → "PostgreSQL"
2. Clique em "Add Service" → "Database" → "Redis"

### 4. Configurar Worker
1. Clique em "Add Service" → "Empty Service"
2. Conecte ao mesmo repositório
3. Set Root Directory = `/backend`
4. Set Start Command = `celery -A app.celery_worker.celery_app worker -l info`

### 5. Configurar Variáveis
Adicione as variáveis de ambiente listadas acima em cada serviço.

## Desenvolvimento Local

### Continua funcionando normalmente:
```bash
# Usar docker-compose para desenvolvimento
docker-compose up -d

# Ou individual
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev
```

### Variáveis locais (.env):
Continue usando seu `.env` atual - as configurações são compatíveis.

## Arquivos Modificados

### Novos arquivos:
- `.env.example` - Template das variáveis de ambiente
- `railway.json` - Configuração do Railway
- `RAILWAY_DEPLOYMENT.md` - Este guia

### Arquivos modificados:
- `backend/Dockerfile` - Otimizado para produção
- `frontend/Dockerfile` - Novo, otimizado para Railway
- `frontend/next.config.mjs` - Configurado para `standalone` output

## Monitoramento

### Railway Dashboard:
- Logs em tempo real
- Métricas de CPU/Memória
- Health checks automáticos

### URLs:
- Frontend: Railway fornece URL automática
- Backend: Railway fornece URL automática 
- Banco: Acessível apenas internamente

## Troubleshooting

### Problemas comuns:
1. **Build falha**: Verifique logs no Railway dashboard
2. **Conexão DB**: Confirme `DATABASE_URL` está configurada
3. **API não conecta**: Verifique `NEXT_PUBLIC_API_URL`
4. **Worker não inicia**: Confirme `REDIS_URL` e comando Celery

### Logs:
```bash
# Ver logs no Railway dashboard ou via CLI
railway logs
```

## Custos Estimados
- **Hobby Plan**: $5/mês por serviço ativo
- **Total**: ~$15-20/mês (backend + frontend + worker)
- **Database**: Inclusos no plano