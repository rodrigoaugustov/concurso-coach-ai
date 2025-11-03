
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from . import models, schemas
from app.users.models import UserContest
from app.contests.models import ContestRole, ProgrammaticContent


def add_message_to_history(db: Session, session_id: int, sender_type: models.SenderType, content: str) -> models.MessageHistory:
    """Adiciona uma nova mensagem ao histórico de uma sessão."""
    db_message = models.MessageHistory(
        session_id=session_id,
        sender_type=sender_type,
        content=content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_full_conversation_history(db: Session, session_id: int):
    """Retorna o histórico completo de mensagens de uma sessão."""
    return db.query(models.MessageHistory).filter(models.MessageHistory.session_id == session_id).order_by(models.MessageHistory.timestamp.asc()).all()