import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum as SQLAlchemyEnum, DateTime
from app.core.database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    contests = relationship("UserContest", back_populates="user", cascade="all, delete-orphan")

class UserContest(Base):
    __tablename__ = "user_contests"

    id = Column(Integer, primary_key=True, index=True)
    
    # CHAVES ESTRANGEIRAS
    user_id = Column(Integer, ForeignKey("users.id"))
    contest_role_id = Column(Integer, ForeignKey("contest_roles.id"))
    
    # RELACIONAMENTOS
    user = relationship("User", back_populates="contests")
    role = relationship("ContestRole", back_populates="user_subscriptions")
    topic_progress = relationship("UserTopicProgress", back_populates="user_contest", cascade="all, delete-orphan")

class AssessmentType(str, enum.Enum):
    SELF_ASSESSMENT = "SELF_ASSESSMENT"
    QUIZ_PRE_STUDY = "QUIZ_PRE_STUDY"
    QUIZ_POST_STUDY = "QUIZ_POST_STUDY"

class UserTopicProgress(Base):
    __tablename__ = "user_topic_progress"

    id = Column(Integer, primary_key=True, index=True)
    current_proficiency_score = Column(Float, default=0.0)
    
    # CHAVES ESTRANGEIRAS
    user_contest_id = Column(Integer, ForeignKey("user_contests.id"))
    programmatic_content_id = Column(Integer, ForeignKey("programmatic_content.id"))
    
    # RELACIONAMENTOS
    user_contest = relationship("UserContest", back_populates="topic_progress")
    topic = relationship("ProgrammaticContent", back_populates="user_progress")
    history = relationship("ProficiencyHistory", back_populates="topic_progress", cascade="all, delete-orphan")

class ProficiencyHistory(Base):
    __tablename__ = "proficiency_history"

    id = Column(Integer, primary_key=True, index=True)
    score = Column(Float, nullable=False)
    assessment_type = Column(SQLAlchemyEnum(AssessmentType), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # CHAVE ESTRANGEIRA: Link para a tabela de progresso do tópico
    user_topic_progress_id = Column(Integer, ForeignKey("user_topic_progress.id"))
    
    # RELACIONAMENTO
    topic_progress = relationship("UserTopicProgress", back_populates="history")