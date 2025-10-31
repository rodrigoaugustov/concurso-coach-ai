from fastapi import FastAPI
from app.core.middleware import setup_middleware  # assume util existente
from app.core.exception_handlers import setup_exception_handlers  # assume util existente

from app.study.router import router as study_router  # já existente
from app.contests.router import router as contests_router  # já existente
from app.study.chat_router import router as chat_router  # novo

app = FastAPI(title="Concurso Coach AI")

setup_middleware(app)
setup_exception_handlers(app)

app.include_router(contests_router)
app.include_router(study_router)
app.include_router(chat_router)
