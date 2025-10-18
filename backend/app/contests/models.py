import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum as SQLAlchemyEnum, Date
from sqlalchemy.orm import relationship
from app.core.database import Base

class ContestStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class PublishedContest(Base):
    __tablename__ = "published_contests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    exam_date = Column(Date, nullable=True)
    status = Column(SQLAlchemyEnum(ContestStatus), nullable=False, default=ContestStatus.PENDING)
    file_url = Column(String, nullable=False)
    file_hash = Column(String, unique=True, index=True)
    error_message = Column(String, nullable=True)
    
    # RELACIONAMENTO: Um concurso tem muitos cargos
    roles = relationship("ContestRole", back_populates="contest", cascade="all, delete-orphan")

class ContestRole(Base):
    __tablename__ = "contest_roles"

    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String, index=True)
    
    # CHAVE ESTRANGEIRA: Link para a tabela de concursos
    published_contest_id = Column(Integer, ForeignKey("published_contests.id"))
   
    # RELACIONAMENTOS
    contest = relationship("PublishedContest", back_populates="roles")
    exam_composition = relationship("ExamComposition", back_populates="role", cascade="all, delete-orphan")
    programmatic_content = relationship("ProgrammaticContent", back_populates="role", cascade="all, delete-orphan")
    user_subscriptions = relationship("UserContest", back_populates="role")


class ExamComposition(Base):
    __tablename__ = "exam_composition"

    id = Column(Integer, primary_key=True, index=True)
    subject_name = Column(String, index=True) 
    number_of_questions = Column(Integer, nullable=True)
    weight_per_question = Column(Float, nullable=True)
    
    # CHAVE ESTRANGEIRA: Link para a tabela de cargos
    contest_role_id = Column(Integer, ForeignKey("contest_roles.id"))
    
    role = relationship("ContestRole", back_populates="exam_composition")

class ProgrammaticContent(Base):
    __tablename__ = "programmatic_content"

    id = Column(Integer, primary_key=True, index=True)
    subject_name = Column(String, index=True)
    topic_group = Column(String, index=True)
    topic_name = Column(String)
    
    # CHAVE ESTRANGEIRA: Link para a tabela de cargos
    contest_role_id = Column(Integer, ForeignKey("contest_roles.id"))
    
    role = relationship("ContestRole", back_populates="programmatic_content")
    
    # RELACIONAMENTO: Um tópico pode ter o progresso de vários usuários
    user_progress = relationship("UserTopicProgress", back_populates="topic")
