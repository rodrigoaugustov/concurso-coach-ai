# Em backend/app/study/schemas.py
from pydantic import BaseModel, Field
from typing import List

class UserContestSubscription(BaseModel):
    id: int
    user_id: int
    contest_role_id: int

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