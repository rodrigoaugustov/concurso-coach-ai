from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings

# Cria o "motor" de conexão com o banco de dados usando a URL do nosso settings.py
engine = create_engine(settings.DATABASE_URL)

# Cria uma fábrica de sessões. Cada instância de SessionLocal será uma sessão de banco de dados.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para nossos modelos ORM. Todos os nossos modelos de dados herdarão desta classe.
Base = declarative_base()

# Função para obter uma sessão de banco de dados (será usada como dependência nos endpoints)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
