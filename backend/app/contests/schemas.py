from datetime import date
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from .models import ContestStatus

# --- Schemas de base, de dentro para fora ---

class ExamCompositionBase(BaseModel):
    subject_name: str
    number_of_questions: Optional[int] = None
    weight_per_question: Optional[float] = None

class ProgrammaticContentBase(BaseModel):
    exam_module: str
    subject: str
    topic: str

class ExamStructure(BaseModel):
    id: int
    level_name: str
    level_type: str 
    number_of_questions: Optional[int] = None
    weight_per_question: Optional[float] = None
    class Config:
        from_attributes = True

class ProgrammaticContent(ProgrammaticContentBase):
    id: int
    class Config:
        from_attributes = True

class ContestRole(BaseModel):
    id: int
    job_title: str
    exam_composition: List[ExamStructure] = []
    programmatic_content: List[ProgrammaticContent] = []
    class Config:
        from_attributes = True

# --- Schema principal ---

class Contest(BaseModel):
    id: int
    name: str
    exam_date: Optional[date] = None
    status: ContestStatus
    file_url: HttpUrl
    file_hash: str
    roles: List[ContestRole] = [] # Inclui a lista de cargos aninhados
    
    class Config:
        from_attributes = True

class ContestBase(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# Schema para o cargo, que inclui o concurso aninhado
class ContestRoleForSubscription(BaseModel):
    id: int
    job_title: str
    contest: ContestBase
    class Config:
        from_attributes = True