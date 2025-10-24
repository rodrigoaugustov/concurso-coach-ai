from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.core.database import engine
from app import models
from app.users.router import router as users_router
from app.contests.router import router as contests_router
from app.study.router import router as study_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.exceptions import CoachAIException
from app.core.exception_handlers import (
    coach_ai_exception_handler,
    validation_exception_handler,
)

# Cria as tabelas no banco de dados
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Concurso Coach AI API",
    description="A API para a plataforma de estudos para concursos.",
    version="0.1.0"
)

# Lista de origens que têm permissão para fazer requisições à nossa API
origins = [
    "http://localhost",
    "http://localhost:3000", # A origem do nosso frontend Next.js em desenvolvimento
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Permite as origens na lista
    allow_credentials=True, # Permite cookies (importante para o futuro)
    allow_methods=["*"],    # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"],    # Permite todos os cabeçalhos
)

# Exception handlers
app.add_exception_handler(CoachAIException, coach_ai_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Inclui os roteadores das diferentes partes da aplicação
app.include_router(users_router, prefix="/api/v1", tags=["Users"])
app.include_router(contests_router, prefix="/api/v1/contests", tags=["Contests"])
app.include_router(study_router, prefix="/api/v1/study", tags=["Study"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
