# Em backend/app/study/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from app.contests.schemas import ProgrammaticContent, ContestRoleForSubscription

class UserContestSubscription(BaseModel):
    id: int
    user_id: int
    contest_role_id: int
    role: ContestRoleForSubscription # <-- CAMPO ADICIONADO

    class Config:
        from_attributes = True

class ProficiencyUpdate(BaseModel):
    subject: str # <-- MUDANÇA: Agora a chave é o 'subject'
    score: float = Field(ge=0.0, le=1.0)

class ProficiencySubmission(BaseModel):
    proficiencies: List[ProficiencyUpdate]

class PlanGenerationResponse(BaseModel):
    status: str
    message: str
    roadmap_items_created: int

class StudySession(BaseModel):
    session_id: int = Field(alias='id')
    session_number: int
    summary: Optional[str] = None
    priority_level: str
    priority_reason: Optional[str] = None
    topics: List[ProgrammaticContent]
    guided_lesson_started: bool = False

    class Config:
        from_attributes = True

class NextStudySessionResponse(BaseModel):
    # Detalhes da sessão principal a ser estudada
    main_session: StudySession # Reutilizamos o schema 'StudySession' que já projetamos
    
    # Tópico opcional para revisão rápida no final da sessão
    review_session: Optional[StudySession] = None

class SessionCompletionRequest(BaseModel):
    main_session_id: int
    review_session_id: Optional[int] = None

class LayoutGenerationRequest(BaseModel):
    topic_ids: List[int]

