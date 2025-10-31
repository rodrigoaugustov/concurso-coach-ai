from __future__ annotations
from typing import Optional
from sqlalchemy.orm import Session
from app.study.models_analytics import ChatAnalytics

class AnalyticsService:
    """Serviço novo e isolado para persistir analytics do chat."""
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        chat_id: str,
        user_id: int,
        phase: str,
        duration_ms: int,
        interaction_source: Optional[str] = None,
        agent: Optional[str] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        meta: Optional[dict] = None,
    ) -> None:
        rec = ChatAnalytics(
            chat_id=chat_id,
            user_id=user_id,
            phase=phase,
            interaction_source=interaction_source,
            agent=agent,
            duration_ms=duration_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            meta=meta or {},
        )
        self.db.add(rec)
        self.db.commit()
