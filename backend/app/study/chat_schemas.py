from __future__ import annotations
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel

class ChatStartRequest(BaseModel):
    """Payload exclusivo do chat para iniciar sessão de aprendizagem guiada.
    Não substitui schemas existentes do módulo study.
    """
    user_contest_id: int
    topic_id: int
    banca: Optional[str] = None

class ChatContinueRequest(BaseModel):
    """Payload exclusivo do chat para continuar sessão (analytics com interaction_source)."""
    message: str
    interaction_source: Optional[Literal["typed", "suggestion"]] = "typed"

class AssistantMessage(BaseModel):
    """Contrato de mensagem do assistente para renderização no frontend (chat)."""
    id: str
    role: Literal["assistant"] = "assistant"
    content: str
    ui_kind: Optional[Literal["explanation", "example", "list", "code", "quiz"]] = None
    agent: Optional[str] = None
    created_at: str

class SuggestionsPayload(BaseModel):
    suggestions: list[str]

class ChatHistoryResponse(BaseModel):
    """Histórico do chat — exclusivo do chat; não interfere em schemas de plano."""
    messages: list[Dict[str, Any]]
    suggestions: Optional[list[str]] = None
