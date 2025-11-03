from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.dialects.postgresql import JSONB

roadmap_session_topics = Table('roadmap_session_topics', Base.metadata,
    Column('session_id', ForeignKey('study_roadmap_sessions.id'), primary_key=True),
    Column('topic_id', ForeignKey('programmatic_content.id'), primary_key=True)
)

class StudyRoadmapSession(Base):
    __tablename__ = "study_roadmap_sessions" # Renomeamos para clareza

    id = Column(Integer, primary_key=True, index=True)
    session_number  = Column(Integer, nullable=False)
    summary = Column(Text, nullable=True) # Text para resumos mais longos
    priority_level = Column(String, nullable=False)
    priority_reason = Column(Text, nullable=True)
    # Armazena o JSON do layout procedural gerado pela IA
    generated_content = Column(JSONB, nullable=True)
    
    # CHAVE ESTRANGEIRA
    user_contest_id = Column(Integer, ForeignKey("user_contests.id"))

    # RELACIONAMENTOS
    user_contest = relationship("UserContest", back_populates="roadmap_sessions")
    messages = relationship("MessageHistory", back_populates="session", cascade="all, delete-orphan")
    
    # NOVO RELACIONAMENTO M-p-M: Uma sessão tem muitos tópicos
    topics = relationship(
        "ProgrammaticContent",
        secondary=roadmap_session_topics,
        back_populates="sessions"
    )