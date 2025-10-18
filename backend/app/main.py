from fastapi import FastAPI
from app.core.database import engine
from app import models
from app.users.router import router as users_router
from app.contests.router import router as contests_router
from app.study.router import router as study_router

# Cria as tabelas no banco de dados
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Concurso Coach AI API",
    description="A API para a plataforma de estudos para concursos.",
    version="0.1.0"
)

# Inclui os roteadores das diferentes partes da aplicação
app.include_router(users_router, prefix="/api/v1", tags=["Users"])
app.include_router(contests_router, prefix="/api/v1/contests", tags=["Contests"])
app.include_router(study_router, prefix="/api/v1/study", tags=["Study"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
