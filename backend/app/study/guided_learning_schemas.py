"""
Schemas for the Guided Learning chat system.
Defines message types, agent responses, and session management models.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime
import uuid


# Request/Response Schemas

class ChatStartRequest(BaseModel):
    """Request to start a new guided learning session."""
    user_contest_id: int
    topic_id: int
    banca: Optional[str] = None


class ChatContinueRequest(BaseModel):
    """Request to continue an existing chat session."""
    message: str
    interaction_source: Optional[Literal["typed", "suggestion"]] = "typed"


class ChatCompleteRequest(BaseModel):
    """Request to complete a chat session."""
    quiz_score: Optional[float] = None


# Message Schemas

class AssistantMessage(BaseModel):
    """Structured assistant message with UI metadata."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Literal["assistant"] = "assistant"
    content: str = Field(description="Message content in markdown format")
    ui_kind: Optional[Literal["explanation", "example", "list", "code", "quiz"]] = None
    agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    suggestions: List[str] = Field(default_factory=list)


class UserMessage(BaseModel):
    """User message in the conversation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Literal["user"] = "user"
    content: str
    interaction_source: Literal["typed", "suggestion"] = "typed"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(BaseModel):
    """Union type for chat messages."""
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    # Optional fields for assistant messages
    ui_kind: Optional[str] = None
    agent: Optional[str] = None
    suggestions: Optional[List[str]] = None
    # Optional fields for user messages
    interaction_source: Optional[str] = None


# Agent Response Schemas

class AgentRouting(BaseModel):
    """Agent routing decision from supervisor."""
    selected_agent: Literal["explanation", "example", "quiz"]
    instructions: str = Field(description="Specific instructions for the selected agent")
    reasoning: Optional[str] = Field(description="Why this agent was selected")


class AgentResponse(BaseModel):
    """Structured response from an agent."""
    content: str = Field(description="Response content in markdown")
    ui_kind: Literal["explanation", "example", "list", "code", "quiz"]
    agent: str = Field(description="Name of the responding agent")
    suggestions: List[str] = Field(description="Suggested follow-up questions/actions")
    next_step: Optional[str] = Field(description="Suggested next step in learning")


class SessionIntroResponse(BaseModel):
    """Response for session introduction."""
    content: str = Field(description="Introduction message in markdown")
    ui_kind: Literal["explanation"] = "explanation"
    agent: Literal["teacher"] = "teacher"
    suggestions: List[str] = Field(description="Initial diagnostic questions")


# Session Management Schemas

class ChatSessionState(BaseModel):
    """Internal state of a chat session."""
    chat_id: str
    user_id: int
    user_contest_id: int
    topic_id: int
    topic_name: str
    subject: str
    proficiency: float
    banca: Optional[str]
    status: Literal["active", "completed", "paused"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    last_agent: Optional[str] = None


class ChatThread(BaseModel):
    """Chat thread information."""
    id: str
    thread_id: str  # LangGraph thread ID
    user_id: int
    user_contest_id: int
    topic_id: int
    banca: Optional[str]
    state: Literal["active", "completed", "paused"] = "active"
    created_at: datetime
    updated_at: datetime


# Response Schemas

class ChatStartResponse(BaseModel):
    """Response when starting a new chat session."""
    chat_id: str
    first_message: AssistantMessage


class ChatContinueResponse(BaseModel):
    """Response when continuing a chat session."""
    message: AssistantMessage


class ChatCompleteResponse(BaseModel):
    """Response when completing a chat session."""
    status: Literal["completed"] = "completed"
    session_summary: Optional[Dict[str, Any]] = None


class ChatHistoryResponse(BaseModel):
    """Response with chat history."""
    messages: List[ChatMessage]
    suggestions: Optional[List[str]] = None
    session_info: Optional[Dict[str, Any]] = None


# Streaming Schemas

class StreamEvent(BaseModel):
    """Base streaming event."""
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DeltaEvent(StreamEvent):
    """Streaming delta content event."""
    event_type: Literal["delta"] = "delta"
    content: str


class FinalEvent(StreamEvent):
    """Final complete message event."""
    event_type: Literal["final"] = "final"
    message: AssistantMessage


class SuggestionsEvent(StreamEvent):
    """Suggestions event."""
    event_type: Literal["suggestions"] = "suggestions"
    suggestions: List[str]


class ErrorEvent(StreamEvent):
    """Error event."""
    event_type: Literal["error"] = "error"
    error: str
    error_code: Optional[str] = None


# Graph State Schema for LangGraph

class ConversationState(BaseModel):
    """State maintained by the LangGraph conversation system."""
    # Session context
    chat_id: str
    user_id: int
    topic_name: str
    subject: str
    proficiency: float
    banca: Optional[str] = None
    
    # Conversation flow
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    current_agent: Optional[str] = None
    last_response: Optional[Dict[str, Any]] = None
    
    # Learning progress
    concepts_covered: List[str] = Field(default_factory=list)
    quiz_attempts: int = 0
    quiz_score: Optional[float] = None
    
    # Flow control
    needs_routing: bool = True
    session_complete: bool = False
    
    class Config:
        arbitrary_types_allowed = True
