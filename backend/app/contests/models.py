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

class ExamLevelType(str, enum.Enum):
    MODULE = "MODULE"
    SUBJECT = "SUBJECT"

class ContestRole(Base):
    __tablename__ = "contest_roles"

    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String, index=True)
    
    # CHAVE ESTRANGEIRA: Link para a tabela de concursos
    published_contest_id = Column(Integer, ForeignKey("published_contests.id"))
   
    # RELACIONAMENTOS
    contest = relationship("PublishedContest", back_populates="roles")
    exam_structure = relationship("ExamStructure", back_populates="role", cascade="all, delete-orphan")
    programmatic_content = relationship("ProgrammaticContent", back_populates="role", cascade="all, delete-orphan")
    programmatic_content = relationship("ProgrammaticContent", back_populates="role", cascade="all, delete-orphan")
    user_subscriptions = relationship("UserContest", back_populates="role")


class ExamStructure(Base):
    __tablename__ = "exam_structure"

    id = Column(Integer, primary_key=True, index=True)
    level_name = Column(String, index=True, nullable=False) # Ex: "Conhecimentos Básicos" ou "Língua Portuguesa"
    level_type = Column(SQLAlchemyEnum(ExamLevelType), nullable=False) # MODULE ou SUBJECT
    number_of_questions = Column(Integer, nullable=True)
    weight_per_question = Column(Float, nullable=True)
    
    # CHAVE ESTRANGEIRA: Link para a tabela de cargos
    contest_role_id = Column(Integer, ForeignKey("contest_roles.id"))
    
    role = relationship("ContestRole", back_populates="exam_structure")

class ProgrammaticContent(Base):
    __tablename__ = "programmatic_content"

    id = Column(Integer, primary_key=True, index=True)
    
    # --- NOVAS COLUNAS HIERÁRQUICAS ---
    exam_module = Column(String, index=True, nullable=False) # Ex: "Conhecimentos Básicos"
    subject = Column(String, index=True, nullable=False)     # Ex: "Língua Portuguesa"
    topic = Column(String, nullable=False)                    # Ex: "Crase"
    
    # CHAVE ESTRANGEIRA (permanece a mesma)
    contest_role_id = Column(Integer, ForeignKey("contest_roles.id"))
    
    # RELACIONAMENTOS (permanecem os mesmos)
    role = relationship("ContestRole", back_populates="programmatic_content")
    progress_entries = relationship("UserTopicProgress", back_populates="topic")
    sessions = relationship(
        "StudyRoadmapSession",
        secondary="roadmap_session_topics",
        back_populates="topics"
    )
