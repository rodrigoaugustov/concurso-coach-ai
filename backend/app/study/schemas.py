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
    topic_group: str
    # A pontuação vai de 0.0 (iniciante) a 1.0 (avançado)
    score: float = Field(ge=0.0, le=1.0) 

class ProficiencySubmission(BaseModel):
    proficiencies: List[ProficiencyUpdate]
