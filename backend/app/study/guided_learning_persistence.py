"""
Persistence layer for guided learning sessions (SQLAlchemy-only, no optional checkpointers).
Handles session state, message history, and thread management.
"""

from typing import Dict, List, Any, Optional, Tuple
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid
import json

from ..core.logging import get_logger
from ..core.settings import get_settings
from .guided_learning_schemas import (
    ChatThread,
    ChatSessionState,
)

Base = declarative_base()


class ChatThreadModel(Base):
    __tablename__ = "chat_threads"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id = Column(String, nullable=False, unique=True)
    user_id = Column(Integer, nullable=False)
    user_contest_id = Column(Integer, nullable=False)
    topic_id = Column(Integer, nullable=False)
    topic_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    proficiency = Column(Float, nullable=False)
    banca = Column(String, nullable=True)
    state = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    message_count = Column(Integer, default=0)
    last_agent = Column(String, nullable=True)


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id = Column(String, nullable=False)
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    ui_kind = Column(String, nullable=True)
    agent = Column(String, nullable=True)
    interaction_source = Column(String, nullable=True)
    suggestions = Column(Text, nullable=True)  # JSON serialized
    created_at = Column(DateTime, default=datetime.utcnow)


class GuidedLearningPersistence:
    def __init__(self):
        self.logger = get_logger("guided_learning_persistence")
        self.settings = get_settings()
        self.engine = create_engine(self.settings.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.logger.info("Guided learning persistence initialized (SQLAlchemy-only)")

    async def create_chat_session(
        self,
        user_id: int,
        user_contest_id: int,
        topic_id: int,
        topic_name: str,
        subject: str,
        proficiency: float,
        banca: Optional[str] = None
    ) -> Tuple[str, str]:
        chat_id = str(uuid.uuid4())
        thread_id = f"chat_{chat_id}"
        
        with self.SessionLocal() as db:
            db.add(ChatThreadModel(
                id=chat_id,
                thread_id=thread_id,
                user_id=user_id,
                user_contest_id=user_contest_id,
                topic_id=topic_id,
                topic_name=topic_name,
                subject=subject,
                proficiency=proficiency,
                banca=banca,
            ))
            db.commit()
        return chat_id, thread_id

    async def get_chat_session(self, chat_id: str) -> Optional[ChatSessionState]:
        with self.SessionLocal() as db:
            t = db.query(ChatThreadModel).filter(ChatThreadModel.id == chat_id).first()
            if not t:
                return None
            return ChatSessionState(
                chat_id=t.id,
                user_id=t.user_id,
                user_contest_id=t.user_contest_id,
                topic_id=t.topic_id,
                topic_name=t.topic_name,
                subject=t.subject,
                proficiency=t.proficiency,
                banca=t.banca,
                status=t.state,
                created_at=t.created_at,
                updated_at=t.updated_at,
                message_count=t.message_count,
                last_agent=t.last_agent,
            )

    async def get_thread_history(self, thread_id: str) -> List[BaseMessage]:
        with self.SessionLocal() as db:
            rows = (
                db.query(ChatMessageModel)
                .filter(ChatMessageModel.thread_id == thread_id)
                .order_by(ChatMessageModel.created_at.asc())
                .all()
            )
            messages: List[BaseMessage] = []
            for r in rows:
                if r.role == "user":
                    messages.append(HumanMessage(content=r.content))
                else:
                    messages.append(AIMessage(content=r.content))
            return messages

    async def save_message(
        self,
        chat_id: str,
        thread_id: str,
        role: str,
        content: str,
        ui_kind: Optional[str] = None,
        agent: Optional[str] = None,
        interaction_source: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
    ) -> str:
        msg_id = str(uuid.uuid4())
        with self.SessionLocal() as db:
            db.add(
                ChatMessageModel(
                    id=msg_id,
                    thread_id=thread_id,
                    role=role,
                    content=content,
                    ui_kind=ui_kind,
                    agent=agent,
                    interaction_source=interaction_source,
                    suggestions=json.dumps(suggestions) if suggestions else None,
                )
            )
            t = db.query(ChatThreadModel).filter(ChatThreadModel.id == chat_id).first()
            if t:
                t.message_count += 1
                t.updated_at = datetime.utcnow()
                if agent:
                    t.last_agent = agent
            db.commit()
        return msg_id

    async def update_session_state(self, chat_id: str, state: str, quiz_score: Optional[float] = None) -> bool:
        with self.SessionLocal() as db:
            t = db.query(ChatThreadModel).filter(ChatThreadModel.id == chat_id).first()
            if not t:
                return False
            t.state = state
            t.updated_at = datetime.utcnow()
            db.commit()
            return True

    async def get_user_active_sessions(self, user_id: int) -> List[ChatThread]:
        with self.SessionLocal() as db:
            rows = (
                db.query(ChatThreadModel)
                .filter(ChatThreadModel.user_id == user_id, ChatThreadModel.state == "active")
                .order_by(ChatThreadModel.updated_at.desc())
                .all()
            )
            return [
                ChatThread(
                    id=r.id,
                    thread_id=r.thread_id,
                    user_id=r.user_id,
                    user_contest_id=r.user_contest_id,
                    topic_id=r.topic_id,
                    banca=r.banca,
                    state=r.state,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in rows
            ]

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        with self.SessionLocal() as db:
            old_threads = (
                db.query(ChatThreadModel)
                .filter(ChatThreadModel.updated_at < cutoff, ChatThreadModel.state != "active")
                .all()
            )
            count = len(old_threads)
            for t in old_threads:
                db.query(ChatMessageModel).filter(ChatMessageModel.thread_id == t.thread_id).delete()
                db.delete(t)
            db.commit()
            return count


_persistence_instance = None

def get_guided_learning_persistence() -> GuidedLearningPersistence:
    global _persistence_instance
    if _persistence_instance is None:
        _persistence_instance = GuidedLearningPersistence()
    return _persistence_instance
