from __future__ import annotations
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.users.models import UserContest

class OwnershipService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_user_contest_topic(self, user_id: int, user_contest_id: int, topic_id: int) -> UserContest:
        uc = self.db.query(UserContest).filter(UserContest.id == user_contest_id, UserContest.user_id == user_id).first()
        if not uc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscrição do usuário não encontrada")
        # TODO: validar se topic_id pertence ao conteúdo do concurso do usuário
        return uc

    def estimate_proficiency(self, user_id: int, topic_id: int) -> int:
        # TODO: calcular pela tabela UserTopicProgress (0..1) e converter para 1..10
        return 5
