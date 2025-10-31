from __future__ annotations
from typing import Optional
from sqlalchemy.orm import Session
from app.users.models import UserContest, UserTopicProgress

class OwnershipService:
    """Valida vínculo do usuário com a inscrição e estima proficiência (exclusivo do chat)."""
    def __init__(self, db: Session):
        self.db = db

    def ensure_user_contest_topic(self, user_id: int, user_contest_id: int, topic_id: int) -> UserContest:
        uc = self.db.query(UserContest).filter(UserContest.id == user_contest_id, UserContest.user_id == user_id).first()
        if not uc:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscrição do usuário não encontrada")
        # TODO: opcional — validar se topic_id pertence ao conteúdo do concurso
        return uc

    def estimate_proficiency(self, user_id: int, topic_id: int) -> int:
        prog = (
            self.db.query(UserTopicProgress)
            .filter(UserTopicProgress.user_id == user_id, UserTopicProgress.topic_id == topic_id)
            .first()
        )
        if not prog or prog.proficiency is None:
            return 5
        try:
            val = float(prog.proficiency)
        except Exception:
            return 5
        val = max(0.0, min(1.0, val))
        scaled = int(round(1 + val * 9))
        return max(1, min(10, scaled))
