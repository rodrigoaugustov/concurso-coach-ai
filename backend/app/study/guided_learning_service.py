"""
Main Guided Learning Service.
Orchestrates multi-agents, persistence, streaming, and session management.
"""

from typing import Dict, List, Any, Optional, AsyncGenerator
from fastapi import HTTPException
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import asyncio
import json
from datetime import datetime

from ..core.ai_service import ChainFactory
from ..core.logging import get_logger
from ..core.settings import get_settings
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
        
        Args:
            user_id: Authenticated user ID
            request: Session start request
        
        Returns:
            Session start response with first message
        """
        self.logger.info(
            "Starting guided learning session",
            user_id=user_id,
            user_contest_id=request.user_contest_id,
            topic_id=request.topic_id
        )
        
        try:
            # Validate user access to contest and topic
            session_context = await self._validate_and_get_context(
                user_id, 
                request.user_contest_id, 
                request.topic_id
            )
            session_context["banca"] = request.banca
            
            # Create new chat session
            chat_id, thread_id = await self.persistence.create_chat_session(
                user_id=user_id,
                user_contest_id=request.user_contest_id,
                topic_id=request.topic_id,
                topic_name=session_context["topic_name"],
                subject=session_context["subject"],
                proficiency=session_context["proficiency"],
                banca=request.banca
            )
            
            # Generate first message using agents
            first_message = await self.agents.start_session(
                chat_id, 
                session_context
            )
            
            # Save the first message
            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="assistant",
                content=first_message.content,
                ui_kind=first_message.ui_kind,
                agent=first_message.agent,
                suggestions=first_message.suggestions
            )
            
            self.logger.info(
                "Session started successfully",
                chat_id=chat_id,
                user_id=user_id
            )
            
            return ChatStartResponse(
                chat_id=chat_id,
                first_message=first_message
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to start session",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start learning session: {str(e)}"
            )
    
    async def continue_session(
        self,
        user_id: int,
        chat_id: str,
        request: ChatContinueRequest
    ) -> ChatContinueResponse:
        """
        Continue an existing chat session.
        
        Args:
            user_id: Authenticated user ID
            chat_id: Chat session ID
            request: Continue request with user message
        
        Returns:
            Response with assistant message
        """
        self.logger.info(
            "Continuing chat session",
            user_id=user_id,
            chat_id=chat_id,
            message_length=len(request.message)
        )
        
        try:
            # Get and validate session
            session = await self.persistence.get_chat_session(chat_id)
            if not session or session.user_id != user_id:
                raise HTTPException(status_code=404, detail="Session not found")
            
            if session.status != "active":
                raise HTTPException(status_code=400, detail="Session is not active")
            
            # Get session context
            session_context = {
                "topic_name": session.topic_name,
                "subject": session.subject,
                "proficiency": session.proficiency,
                "banca": session.banca
            }
            
            # Get message history
            thread_id = f"chat_{chat_id}"
            message_history = await self.persistence.get_thread_history(thread_id)
            
            # Save user message
            user_msg_id = await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="user",
                content=request.message,
                interaction_source=request.interaction_source
            )
            
            # Process through multi-agent system
            assistant_message = await self.agents.process_message(
                chat_id=chat_id,
                user_id=user_id,
                user_message=request.message,
                session_context=session_context,
                message_history=message_history
            )
            
            # Save assistant message
            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="assistant",
                content=assistant_message.content,
                ui_kind=assistant_message.ui_kind,
                agent=assistant_message.agent,
                suggestions=assistant_message.suggestions
            )
            
            self.logger.info(
                "Session continued successfully",
                chat_id=chat_id,
                agent=assistant_message.agent
            )
            
            return ChatContinueResponse(message=assistant_message)
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to continue session",
                user_id=user_id,
                chat_id=chat_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to continue session: {str(e)}"
            )
    
    async def continue_session_stream(
        self,
        user_id: int,
        chat_id: str,
        request: ChatContinueRequest
    ) -> AsyncGenerator[str, None]:
        """
        Continue session with streaming response.
        
        Args:
            user_id: Authenticated user ID
            chat_id: Chat session ID
            request: Continue request
        
        Yields:
            Server-sent events as JSON strings
        """
        self.logger.info(
            "Starting streaming session continue",
            user_id=user_id,
            chat_id=chat_id
        )
        
        try:
            # Validate session (same as non-streaming)
            session = await self.persistence.get_chat_session(chat_id)
            if not session or session.user_id != user_id:
                error_event = ErrorEvent(
                    error="Session not found",
                    error_code="SESSION_NOT_FOUND"
                )
                yield f"data: {error_event.json()}\n\n"
                return
            
            if session.status != "active":
                error_event = ErrorEvent(
                    error="Session is not active",
                    error_code="SESSION_INACTIVE"
                )
                yield f"data: {error_event.json()}\n\n"
                return
            
            # Get context and history
            session_context = {
                "topic_name": session.topic_name,
                "subject": session.subject,
                "proficiency": session.proficiency,
                "banca": session.banca
            }
            
            thread_id = f"chat_{chat_id}"
            message_history = await self.persistence.get_thread_history(thread_id)
            
            # Save user message
            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="user",
                content=request.message,
                interaction_source=request.interaction_source
            )
            
            # Stream the response from agents
            accumulated_content = ""
            
            # For now, we'll simulate streaming by processing normally and chunking
            # In a full implementation, we'd modify the agent system to support streaming
            assistant_message = await self.agents.process_message(
                chat_id=chat_id,
                user_id=user_id,
                user_message=request.message,
                session_context=session_context,
                message_history=message_history
            )
            
            # Simulate streaming by chunking the response
            content = assistant_message.content
            chunk_size = 20  # Characters per chunk
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                accumulated_content += chunk
                
                delta_event = DeltaEvent(content=chunk)
                yield f"data: {delta_event.json()}\n\n"
                
                # Small delay to simulate streaming
                await asyncio.sleep(0.1)
            
            # Send final message
            final_event = FinalEvent(message=assistant_message)
            yield f"data: {final_event.json()}\n\n"
            
            # Send suggestions
            if assistant_message.suggestions:
                suggestions_event = SuggestionsEvent(
                    suggestions=assistant_message.suggestions
                )
                yield f"data: {suggestions_event.json()}\n\n"
            
            # Save assistant message
            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="assistant",
                content=assistant_message.content,
                ui_kind=assistant_message.ui_kind,
                agent=assistant_message.agent,
                suggestions=assistant_message.suggestions
            )
            
            self.logger.info(
                "Streaming session completed",
                chat_id=chat_id,
                agent=assistant_message.agent
            )
            
        except Exception as e:
            self.logger.error(
                "Streaming session failed",
                user_id=user_id,
                chat_id=chat_id,
                error=str(e)
            )
            
            error_event = ErrorEvent(
                error=str(e),
                error_code="PROCESSING_ERROR"
            )
            yield f"data: {error_event.json()}\n\n"
    
    async def complete_session(
        self,
        user_id: int,
        chat_id: str,
        request: ChatCompleteRequest
    ) -> ChatCompleteResponse:
        """
        Complete a chat session.
        
        Args:
            user_id: Authenticated user ID
            chat_id: Chat session ID
            request: Completion request
        
        Returns:
            Completion response
        """
        self.logger.info(
            "Completing chat session",
            user_id=user_id,
            chat_id=chat_id,
            quiz_score=request.quiz_score
        )
        
        try:
            # Validate session
            session = await self.persistence.get_chat_session(chat_id)
            if not session or session.user_id != user_id:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Update session state
            success = await self.persistence.update_session_state(
                chat_id=chat_id,
                state="completed",
                quiz_score=request.quiz_score
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to complete session")
            
            # TODO: Schedule spaced repetition and update progress
            # This would integrate with existing study services
            
            session_summary = {
                "topic_name": session.topic_name,
                "subject": session.subject,
                "duration_minutes": (
                    datetime.utcnow() - session.created_at
                ).total_seconds() / 60,
                "message_count": session.message_count,
                "quiz_score": request.quiz_score
            }
            
            self.logger.info(
                "Session completed successfully",
                chat_id=chat_id,
                user_id=user_id
            )
            
            return ChatCompleteResponse(
                status="completed",
                session_summary=session_summary
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to complete session",
                user_id=user_id,
                chat_id=chat_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to complete session: {str(e)}"
            )
    
    async def get_session_history(
        self,
        user_id: int,
        chat_id: str
    ) -> ChatHistoryResponse:
        """
        Get chat session history.
        
        Args:
            user_id: Authenticated user ID
            chat_id: Chat session ID
        
        Returns:
            Chat history response
        """
        self.logger.info(
            "Getting session history",
            user_id=user_id,
            chat_id=chat_id
        )
        
        try:
            # Validate session
            session = await self.persistence.get_chat_session(chat_id)
            if not session or session.user_id != user_id:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Get message history from database
            # For simplicity, we'll get from LangGraph history
            thread_id = f"chat_{chat_id}"
            message_history = await self.persistence.get_thread_history(thread_id)
            
            # Convert to chat messages
            messages = []
            for msg in message_history:
                if isinstance(msg, HumanMessage):
                    messages.append({
                        "id": f"user_{len(messages)}",
                        "role": "user",
                        "content": msg.content,
                        "created_at": datetime.utcnow().isoformat()
                    })
                elif isinstance(msg, AIMessage):
                    messages.append({
                        "id": f"assistant_{len(messages)}",
                        "role": "assistant",
                        "content": msg.content,
                        "created_at": datetime.utcnow().isoformat()
                    })
            
            session_info = {
                "chat_id": chat_id,
                "topic_name": session.topic_name,
                "subject": session.subject,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "message_count": len(messages)
            }
            
            return ChatHistoryResponse(
                messages=messages,
                session_info=session_info
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to get session history",
                user_id=user_id,
                chat_id=chat_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get session history: {str(e)}"
            )
    
    async def _validate_and_get_context(
        self,
        user_id: int,
        user_contest_id: int,
        topic_id: int
    ) -> Dict[str, Any]:
        """
        Validate user access and get session context.
        
        Args:
            user_id: User ID
            user_contest_id: User contest ID
            topic_id: Topic ID
        
        Returns:
            Session context dictionary
        
        Raises:
            HTTPException: If validation fails
        """
        # TODO: Implement proper validation with database queries
        # For now, return mock context
        
        # In a real implementation, this would:
        # 1. Verify user owns the user_contest_id
        # 2. Verify topic_id exists in the contest
        # 3. Get topic details (name, subject, user proficiency)
        
        return {
            "topic_name": "Direito Constitucional - Princípios Fundamentais",
            "subject": "Direito Constitucional",
            "proficiency": 0.6  # User's current proficiency (0.0 to 1.0)
        }


# Global service instance
_service_instance = None

def get_guided_learning_service() -> GuidedLearningService:
    """Get or create the global service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = GuidedLearningService()
    return _service_instance
