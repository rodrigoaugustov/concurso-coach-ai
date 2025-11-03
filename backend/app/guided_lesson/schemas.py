
from pydantic import BaseModel
from datetime import datetime
from typing import List
from .models import GuidedLessonStatus, SenderType
from app.study.schemas import StudySession

# ======== Base Schemas ========

class MessageHistoryBase(BaseModel):
    sender_type: SenderType
    content: str

class MessageHistoryInDB(MessageHistoryBase):
    id: int
    timestamp: datetime
    session_id: int

    class Config:
        from_attributes = True

# ======== API Schemas ========

class LessonStartRequest(BaseModel):
    session_contents: StudySession

class LessonStartResponse(BaseModel):
    session_id: int
    message: str

class ChatMessageRequest(BaseModel):
    content: str
    session_contents: StudySession

class ChatMessageResponse(BaseModel):
    agent_response: str
    history: List[MessageHistoryInDB]
