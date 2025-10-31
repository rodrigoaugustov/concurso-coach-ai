from __future__ import annotations
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel

class ChatStartRequest(BaseModel):
    user_contest_id: int
    topic_id: int
    banca: Optional[str] = None

class ChatContinueRequest(BaseModel):
    message: str
    interaction_source: Optional[Literal["typed", "suggestion"]] = "typed"

class AssistantMessage(BaseModel):
    id: str
    role: Literal["assistant"] = "assistant"
    content: str
    ui_kind: Optional[Literal["explanation", "example", "list", "code", "quiz"]] = None
    agent: Optional[str] = None
    created_at: str

class SuggestionsPayload(BaseModel):
    suggestions: list[str]

class ChatHistoryResponse(BaseModel):
    messages: list[Dict[str, Any]]
    suggestions: Optional[list[str]] = None
