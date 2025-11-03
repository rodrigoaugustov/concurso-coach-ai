
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLAlchemyEnum, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class GuidedLessonStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class SenderType(str, enum.Enum):
    USER = "USER"
    AI = "AI"

class MessageHistory(Base):
    __tablename__ = "message_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender_type = Column(SQLAlchemyEnum(SenderType), nullable=False)
    content = Column(Text, nullable=False)

    # Foreign Key
    session_id = Column(Integer, ForeignKey("study_roadmap_sessions.id"), nullable=False)

    # Relationship
    session = relationship("StudyRoadmapSession", back_populates="messages")
