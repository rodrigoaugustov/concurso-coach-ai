"""
Main Guided Learning Service.
Orchestrates multi-agents, persistence, streaming, and session management.
"""

from typing import Dict, List, Any, Optional, AsyncGenerator
from fastapi import HTTPException
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy.orm import Session
import asyncio
import json
from datetime import datetime

from ..core.ai_service import ChainFactory
from ..core.logging import get_logger
from ..core.settings import get_settings
from ..core.database import get_db
from ..users.models import UserContest, UserTopicProgress
from ..contests.models import ProgrammaticContent, ContestRole
from .guided_learning_agents import GuidedLearningAgents
from .guided_learning_persistence import get_guided_learning_persistence
from .guided_learning_schemas import (
    ChatStartRequest,
    ChatContinueRequest,
    ChatCompleteRequest,
    ChatStartResponse,
    ChatContinueResponse,
    ChatCompleteResponse,
    ChatHistoryResponse,
    AssistantMessage,
    UserMessage,
    StreamEvent,
    DeltaEvent,
    FinalEvent,
    SuggestionsEvent,
    ErrorEvent
)


class GuidedLearningService:
    """
    Main service for guided learning chat functionality.
    Coordinates agents, persistence, streaming, and business logic.
    """

    def __init__(self):
        self.logger = get_logger("guided_learning_service")
        self.settings = get_settings()
        
        # Initialize components
        self.chain_factory = ChainFactory(
            provider="google",
            api_key=self.settings.gemini_api_key,
            model_name="gemini-1.5-flash",
            temperature=0.3
        )
        
        self.agents = GuidedLearningAgents(self.chain_factory)
        self.persistence = get_guided_learning_persistence()
        
        self.logger.info("Guided learning service initialized")
    
    async def start_session(
        self,
        user_id: int,
        request: ChatStartRequest
    ) -> ChatStartResponse:
        """
        Start a new guided learning session.
        """
        self.logger.info(
            "Starting guided learning session",
            user_id=user_id,
            user_contest_id=request.user_contest_id,
            topic_id=request.topic_id
        )
        
        try:
            session_context = await self._validate_and_get_context(
                user_id, 
                request.user_contest_id, 
                request.topic_id
            )
            session_context["banca"] = request.banca
            chat_id, thread_id = await self.persistence.create_chat_session(
                user_id=user_id,
                user_contest_id=request.user_contest_id,
                topic_id=request.topic_id,
                topic_name=session_context["topic_name"],
                subject=session_context["subject"],
                proficiency=session_context["proficiency"],
                banca=request.banca
            )
            first_message = await self.agents.start_session(
                chat_id, 
                session_context
            )
            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="assistant",
                content=first_message.content,
                ui_kind=first_message.ui_kind,
                agent=first_message.agent,
                suggestions=first_message.suggestions
            )
            self.logger.info("Session started successfully", chat_id=chat_id, user_id=user_id)
            return ChatStartResponse(chat_id=chat_id, first_message=first_message)
        
        except Exception as e:
            self.logger.error("Failed to start session", user_id=user_id, error=str(e), error_type=type(e).__name__)
            raise HTTPException(status_code=500, detail=f"Failed to start learning session: {str(e)}")
    
    async def continue_session(
        self,
        user_id: int,
        chat_id: str,
        request: ChatContinueRequest
    ) -> ChatContinueResponse:
        """
        Continue an existing chat session.
        """
        self.logger.info("Continuing chat session", user_id=user_id, chat_id=chat_id, message_length=len(request.message))
        
        try:
            session = await self.persistence.get_chat_session(chat_id)
            if not session or session.user_id != user_id:
                raise HTTPException(status_code=404, detail="Session not found")
            if session.status != "active":
                raise HTTPException(status_code=400, detail="Session is not active")
            session_context = {
                "topic_name": session.topic_name,
                "subject": session.subject,
                "proficiency": session.proficiency,
                "banca": session.banca
            }
            thread_id = f"chat_{chat_id}"
            message_history = await self.persistence.get_thread_history(thread_id)
            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="user",
                content=request.message,
                interaction_source=request.interaction_source
            )
            assistant_message = await self.agents.process_message(
                chat_id=chat_id,
                user_id=user_id,
                user_message=request.message,
                session_context=session_context,
                message_history=message_history
            )
            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="assistant",
                content=assistant_message.content,
                ui_kind=assistant_message.ui_kind,
                agent=assistant_message.agent,
                suggestions=assistant_message.suggestions
            )
            self.logger.info("Session continued successfully", chat_id=chat_id, agent=assistant_message.agent)
            return ChatContinueResponse(message=assistant_message)
        
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error("Failed to continue session", user_id=user_id, chat_id=chat_id, error=str(e), error_type=type(e).__name__)
            raise HTTPException(status_code=500, detail=f"Failed to continue session: {str(e)}")
    
    async def continue_session_stream(
        self,
        user_id: int,
        chat_id: str,
        request: ChatContinueRequest
    ) -> AsyncGenerator[str, None]:
        """
        Continue session with real streaming response using LangChain astream.
        """
        self.logger.info("Starting streaming session continue", user_id=user_id, chat_id=chat_id)
        
        try:
            session = await self.persistence.get_chat_session(chat_id)
            if not session or session.user_id != user_id:
                error_event = ErrorEvent(error="Session not found", error_code="SESSION_NOT_FOUND")
                yield f"data: {error_event.json()}\n\n"; return
            if session.status != "active":
                error_event = ErrorEvent(error="Session is not active", error_code="SESSION_INACTIVE")
                yield f"data: {error_event.json()}\n\n"; return
            session_context = {
                "topic_name": session.topic_name,
                "subject": session.subject,
                "proficiency": session.proficiency,
                "banca": session.banca
            }
            thread_id = f"chat_{chat_id}"
            message_history = await self.persistence.get_thread_history(thread_id)
            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="user",
                content=request.message,
                interaction_source=request.interaction_source
            )
            agent_type = self._simple_route(request.message)
            stream_context = {
                "topic_name": session_context["topic_name"],
                "subject": session_context["subject"],
                "proficiency": int(session_context["proficiency"] * 10),
                "banca": session_context.get("banca", "Não especificada"),
                "supervisor_instructions": f"Responda como agente {agent_type} sobre '{request.message}'",
                # IMPORTANT: pass list[BaseMessage] to MessagesPlaceholder
                "messages": message_history + [HumanMessage(content=request.message)],
            }
            template_name = f"{agent_type}_agent"
            accumulated_content = ""
            try:
                async for chunk in self.chain_factory.astream(template_name, stream_context):
                    if chunk:
                        accumulated_content += chunk
                        yield f"data: {DeltaEvent(content=chunk).json()}\n\n"
            except Exception as e:
                self.logger.warning("Real streaming failed, using fallback", error=str(e))
                # Fallback to non-streaming
                assistant_message = await self.agents.process_message(
                    chat_id=chat_id,
                    user_id=user_id,
                    user_message=request.message,
                    session_context=session_context,
                    message_history=message_history
                )
                content = assistant_message.content
                chunk_size = 25
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    accumulated_content += chunk
                    yield f"data: {DeltaEvent(content=chunk).json()}\n\n"
                    await asyncio.sleep(0.05)
            suggestions = self._generate_suggestions_for_agent(agent_type)
            final_message = AssistantMessage(
                content=accumulated_content,
                ui_kind=agent_type if agent_type in ["explanation", "example", "quiz"] else "explanation",
                agent=agent_type,
                suggestions=suggestions
            )
            yield f"data: {FinalEvent(message=final_message).json()}\n\n"
            yield f"data: {SuggestionsEvent(suggestions=suggestions).json()}\n\n"
            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="assistant",
                content=accumulated_content,
                ui_kind=final_message.ui_kind,
                agent=final_message.agent,
                suggestions=suggestions
            )
            self.logger.info("Real streaming session completed", chat_id=chat_id, agent=agent_type, content_length=len(accumulated_content))
        except Exception as e:
            self.logger.error("Streaming session failed", user_id=user_id, chat_id=chat_id, error=str(e))
            yield f"data: {ErrorEvent(error=str(e), error_code="PROCESSING_ERROR").json()}\n\n"
    
    def _simple_route(self, message: str) -> str:
        text = message.lower()
        if any(w in text for w in ["quiz", "teste", "avaliação", "questão", "exercício", "praticar", "treinar", "avaliar", "verificar"]):
            return "quiz"
        if any(w in text for w in ["exemplo", "prático", "aplicação", "como fazer", "na prática", "caso real", "situação", "demonstre", "mostre"]):
            return "example"
        return "explanation"

    # ... rest of file unchanged ...
