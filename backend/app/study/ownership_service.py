from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session
from app.users.models import UserTopicProgress

class OwnershipService:
    def __init__(self, db: Session):
        self.db = db

    def estimate_proficiency(self, user_id: int, topic_id: int) -> int:
        """Calcula proficiência real do usuário no tópico (1..10).
        Regra:
        - Busca UserTopicProgress.proficiency (0..1)
        - Converte para escala 1..10 (mín 1)
        - Arredonda para inteiro
        """
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
