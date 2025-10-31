from __future__ annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.core.database import Base

class ChatAnalytics(Base):
    """Modelo novo para analytics do chat (requer migration). Não altera modelos existentes."""
    __tablename__ = "chat_analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    phase = Column(String, nullable=False)  # start|continue
    interaction_source = Column(String, nullable=True)  # typed|suggestion
    agent = Column(String, nullable=True)  # explanation|example|quiz
    duration_ms = Column(Integer, nullable=False)
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    meta = Column(JSON, nullable=True)
