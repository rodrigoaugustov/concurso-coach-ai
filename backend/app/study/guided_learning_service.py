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
            
            # Update user topic progress if quiz score provided
            if request.quiz_score is not None:
                await self._update_topic_progress(
                    session.user_contest_id,
                    session.topic_id,
                    request.quiz_score
                )
            
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
            topic_id: Topic ID (ProgrammaticContent.id)
        
        Returns:
            Session context dictionary
        
        Raises:
            HTTPException: If validation fails
        """
        
        # Get database session
        db: Session = next(get_db())
        
        try:
            # 1. Verify user owns the user_contest_id
            user_contest = db.query(UserContest).filter(
                UserContest.id == user_contest_id,
                UserContest.user_id == user_id
            ).first()
            
            if not user_contest:
                raise HTTPException(
                    status_code=404, 
                    detail="User contest not found or access denied"
                )
            
            # 2. Verify topic_id exists and belongs to this contest
            topic = db.query(ProgrammaticContent).filter(
                ProgrammaticContent.id == topic_id,
                ProgrammaticContent.contest_role_id == user_contest.contest_role_id
            ).first()
            
            if not topic:
                raise HTTPException(
                    status_code=404,
                    detail="Topic not found in this contest"
                )
            
            # 3. Get user's current proficiency for this topic
            topic_progress = db.query(UserTopicProgress).filter(
                UserTopicProgress.user_contest_id == user_contest_id,
                UserTopicProgress.programmatic_content_id == topic_id
            ).first()
            
            # If no progress record exists, create one with default proficiency
            if not topic_progress:
                topic_progress = UserTopicProgress(
                    user_contest_id=user_contest_id,
                    programmatic_content_id=topic_id,
                    current_proficiency_score=0.3,  # Default starting proficiency
                    sessions_studied=0
                )
                db.add(topic_progress)
                db.commit()
                db.refresh(topic_progress)
                
                self.logger.info(
                    "Created new topic progress record",
                    user_id=user_id,
                    topic_id=topic_id,
                    initial_proficiency=0.3
                )
            
            self.logger.info(
                "Session context validated",
                user_id=user_id,
                user_contest_id=user_contest_id,
                topic_id=topic_id,
                topic_name=topic.topic,
                subject=topic.subject,
                proficiency=topic_progress.current_proficiency_score
            )
            
            return {
                "topic_name": topic.topic,
                "subject": topic.subject,
                "exam_module": topic.exam_module,
                "proficiency": topic_progress.current_proficiency_score,
                "sessions_studied": topic_progress.sessions_studied
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(
                "Session context validation failed",
                user_id=user_id,
                user_contest_id=user_contest_id,
                topic_id=topic_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to validate session context"
            )
        finally:
            db.close()
    
    async def _update_topic_progress(
        self,
        user_contest_id: int,
        topic_id: int,
        quiz_score: float
    ) -> None:
        """
        Update user's topic progress based on quiz performance.
        
        Args:
            user_contest_id: User contest ID
            topic_id: Topic ID
            quiz_score: Quiz score (0.0 to 1.0)
        """
        db: Session = next(get_db())
        
        try:
            # Get existing progress
            progress = db.query(UserTopicProgress).filter(
                UserTopicProgress.user_contest_id == user_contest_id,
                UserTopicProgress.programmatic_content_id == topic_id
            ).first()
            
            if progress:
                # Update proficiency using weighted average
                # New proficiency = 70% old + 30% quiz score
                new_proficiency = (0.7 * progress.current_proficiency_score) + (0.3 * quiz_score)
                new_proficiency = max(0.0, min(1.0, new_proficiency))  # Clamp to [0, 1]
                
                progress.current_proficiency_score = new_proficiency
                progress.sessions_studied += 1
                progress.last_studied_at = datetime.utcnow()
                
                # Schedule next review (simple spaced repetition)
                if quiz_score >= 0.8:  # Good performance
                    next_review_days = 7
                elif quiz_score >= 0.6:  # Average performance  
                    next_review_days = 3
                else:  # Poor performance
                    next_review_days = 1
                
                from datetime import timedelta
                progress.next_review_at = datetime.utcnow() + timedelta(days=next_review_days)
                
                db.commit()
                
                self.logger.info(
                    "Topic progress updated",
                    user_contest_id=user_contest_id,
                    topic_id=topic_id,
                    old_proficiency=progress.current_proficiency_score,
                    new_proficiency=new_proficiency,
                    quiz_score=quiz_score,
                    next_review_days=next_review_days
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to update topic progress",
                user_contest_id=user_contest_id,
                topic_id=topic_id,
                error=str(e)
            )
            db.rollback()
        finally:
            db.close()


# Global service instance
_service_instance = None

def get_guided_learning_service() -> GuidedLearningService:
    """Get or create the global service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = GuidedLearningService()
    return _service_instance
