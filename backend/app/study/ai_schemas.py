# Em backend/app/study/ai_schemas.py
from pydantic import BaseModel, Field
from typing import List

# --- Schema para a SAÍDA da Chamada 1 (Análise) ---
class AITopicAnalysis(BaseModel):
    topic_id: int
    priority_level: str = Field(description="Urgente, Alta Prioridade, Média Prioridade, ou Baixa Prioridade.")
    estimated_sessions: int = Field(description="Número de sessões de 30 min estimadas para este tópico.")
    prerequisite_topic_ids: List[int] = Field(description="Lista de IDs de tópicos que são pré-requisitos diretos.")

class AITopicAnalysisResponse(BaseModel):
    analyzed_topics: List[AITopicAnalysis]

# --- Schema para a SAÍDA da Chamada 2 (Organização do Plano) ---
class AIRoadmapSession(BaseModel):
    session_number: int
    topic_ids: List[int]
    summary: str
    priority_level: str
    priority_reason: str

class AIStudyPlanResponse(BaseModel):
    roadmap: List[AIRoadmapSession]