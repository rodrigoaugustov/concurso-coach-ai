"""
Persistence layer for guided learning sessions using LangGraph PostgreSQL Checkpointer.
Handles session state, message history, and thread management.
"""

from typing import Dict, List, Any, Optional, Tuple
from langchain_postgres import PostgresCheckpointSaver
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import uuid
import json

from ..core.database import get_db
from ..core.logging import get_logger
from ..core.settings import get_settings
from .guided_learning_schemas import (
    ChatThread,
    ChatSessionState,
    ChatMessage,
    ConversationState
)

Base = declarative_base()


class ChatThreadModel(Base):
    """Database model for chat threads."""
    __tablename__ = "chat_threads"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id = Column(String, nullable=False, unique=True)  # LangGraph thread ID
    user_id = Column(Integer, nullable=False)
    user_contest_id = Column(Integer, nullable=False)
    topic_id = Column(Integer, nullable=False)
    topic_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    proficiency = Column(Float, nullable=False)
    banca = Column(String, nullable=True)
    state = Column(String, default="active")  # active, completed, paused
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    message_count = Column(Integer, default=0)
    last_agent = Column(String, nullable=True)


class ChatMessageModel(Base):
    """Database model for chat messages (optional - LangGraph handles most persistence)."""
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id = Column(String, nullable=False)
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    ui_kind = Column(String, nullable=True)
    agent = Column(String, nullable=True)
    interaction_source = Column(String, nullable=True)
    suggestions = Column(Text, nullable=True)  # JSON serialized
    created_at = Column(DateTime, default=datetime.utcnow)


class GuidedLearningPersistence:
    """
    Persistence manager for guided learning sessions.
    Combines LangGraph checkpointer with custom business logic.
    """
    
    def __init__(self):
        self.logger = get_logger("guided_learning_persistence")
        self.settings = get_settings()
        
        # Initialize database connection
        self.engine = create_engine(self.settings.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize LangGraph checkpointer
        self.checkpointer = PostgresCheckpointSaver.from_conn_string(
            self.settings.database_url
        )
        
        # Create tables if needed
        Base.metadata.create_all(self.engine)
        
        self.logger.info("Guided learning persistence initialized")
    
    async def create_chat_session(
        self,
        user_id: int,
        user_contest_id: int,
        topic_id: int,
        topic_name: str,
        subject: str,
        proficiency: float,
        banca: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create a new chat session and return chat_id and thread_id.
        
        Returns:
            Tuple of (chat_id, thread_id)
        """
        chat_id = str(uuid.uuid4())
        thread_id = f"chat_{chat_id}"
        
        self.logger.info(
            "Creating new chat session",
            chat_id=chat_id,
            user_id=user_id,
            topic_name=topic_name
        )
        
        try:
            # Create database record
            with self.SessionLocal() as db:
                chat_thread = ChatThreadModel(
                    id=chat_id,
                    thread_id=thread_id,
                    user_id=user_id,
                    user_contest_id=user_contest_id,
                    topic_id=topic_id,
                    topic_name=topic_name,
                    subject=subject,
                    proficiency=proficiency,
                    banca=banca
                )
                
                db.add(chat_thread)
                db.commit()
            
            # Initialize checkpointer state
            initial_state = ConversationState(
                chat_id=chat_id,
                user_id=user_id,
                topic_name=topic_name,
                subject=subject,
                proficiency=proficiency,
                banca=banca
            )
            
            # Save initial state to checkpointer
            config = {"configurable": {"thread_id": thread_id}}
            await self.checkpointer.aput(
                config,
                {
                    "state": initial_state.dict(),
                    "metadata": {
                        "created_at": datetime.utcnow().isoformat(),
                        "user_id": user_id,
                        "topic_name": topic_name
                    }
                }
            )
            
            self.logger.info(
                "Chat session created successfully",
                chat_id=chat_id,
                thread_id=thread_id
            )
            
            return chat_id, thread_id
            
        except Exception as e:
            self.logger.error(
                "Failed to create chat session",
                chat_id=chat_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def get_chat_session(
        self, 
        chat_id: str
    ) -> Optional[ChatSessionState]:
        """Get chat session state by chat_id."""
        
        self.logger.debug("Getting chat session", chat_id=chat_id)
        
        try:
            with self.SessionLocal() as db:
                thread_model = db.query(ChatThreadModel).filter(
                    ChatThreadModel.id == chat_id
                ).first()
                
                if not thread_model:
                    return None
                
                # Convert to schema
                return ChatSessionState(
                    chat_id=thread_model.id,
                    user_id=thread_model.user_id,
                    user_contest_id=thread_model.user_contest_id,
                    topic_id=thread_model.topic_id,
                    topic_name=thread_model.topic_name,
                    subject=thread_model.subject,
                    proficiency=thread_model.proficiency,
                    banca=thread_model.banca,
                    status=thread_model.state,
                    created_at=thread_model.created_at,
                    updated_at=thread_model.updated_at,
                    message_count=thread_model.message_count,
                    last_agent=thread_model.last_agent
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to get chat session",
                chat_id=chat_id,
                error=str(e)
            )
            return None
    
    async def get_thread_history(
        self, 
        thread_id: str
    ) -> List[BaseMessage]:
        """
        Get conversation history for a thread from LangGraph checkpointer.
        
        Args:
            thread_id: LangGraph thread identifier
        
        Returns:
            List of conversation messages
        """
        self.logger.debug("Getting thread history", thread_id=thread_id)
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # Get latest checkpoint
            checkpoint = await self.checkpointer.aget(config)
            
            if not checkpoint:
                return []
            
            # Extract messages from checkpoint state
            state_data = checkpoint.get("state", {})
            messages_data = state_data.get("messages", [])
            
            # Convert to BaseMessage objects
            messages = []
            for msg_data in messages_data:
                if msg_data.get("type") == "human":
                    messages.append(HumanMessage(content=msg_data["content"]))
                elif msg_data.get("type") == "ai":
                    messages.append(AIMessage(content=msg_data["content"]))
            
            return messages
            
        except Exception as e:
            self.logger.error(
                "Failed to get thread history",
                thread_id=thread_id,
                error=str(e)
            )
            return []
    
    async def save_message(
        self,
        chat_id: str,
        thread_id: str,
        role: str,
        content: str,
        ui_kind: Optional[str] = None,
        agent: Optional[str] = None,
        interaction_source: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ) -> str:
        """
        Save a message to the database (optional persistence beyond LangGraph).
        
        Returns:
            Message ID
        """
        message_id = str(uuid.uuid4())
        
        try:
            with self.SessionLocal() as db:
                message = ChatMessageModel(
                    id=message_id,
                    thread_id=thread_id,
                    role=role,
                    content=content,
                    ui_kind=ui_kind,
                    agent=agent,
                    interaction_source=interaction_source,
                    suggestions=json.dumps(suggestions) if suggestions else None
                )
                
                db.add(message)
                
                # Update thread message count
                thread = db.query(ChatThreadModel).filter(
                    ChatThreadModel.id == chat_id
                ).first()
                
                if thread:
                    thread.message_count += 1
                    thread.updated_at = datetime.utcnow()
                    if agent:
                        thread.last_agent = agent
                
                db.commit()
            
            return message_id
            
        except Exception as e:
            self.logger.error(
                "Failed to save message",
                chat_id=chat_id,
                error=str(e)
            )
            raise
    
    async def update_session_state(
        self,
        chat_id: str,
        state: str,
        quiz_score: Optional[float] = None
    ) -> bool:
        """
        Update session state (active, completed, paused).
        
        Args:
            chat_id: Chat session ID
            state: New state value
            quiz_score: Optional quiz score for completed sessions
        
        Returns:
            True if successful
        """
        self.logger.info(
            "Updating session state",
            chat_id=chat_id,
            new_state=state
        )
        
        try:
            with self.SessionLocal() as db:
                thread = db.query(ChatThreadModel).filter(
                    ChatThreadModel.id == chat_id
                ).first()
                
                if thread:
                    thread.state = state
                    thread.updated_at = datetime.utcnow()
                    db.commit()
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to update session state",
                chat_id=chat_id,
                error=str(e)
            )
            return False
    
    async def get_user_active_sessions(
        self, 
        user_id: int
    ) -> List[ChatThread]:
        """
        Get all active chat sessions for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            List of active chat threads
        """
        try:
            with self.SessionLocal() as db:
                threads = db.query(ChatThreadModel).filter(
                    ChatThreadModel.user_id == user_id,
                    ChatThreadModel.state == "active"
                ).order_by(ChatThreadModel.updated_at.desc()).all()
                
                return [
                    ChatThread(
                        id=t.id,
                        thread_id=t.thread_id,
                        user_id=t.user_id,
                        user_contest_id=t.user_contest_id,
                        topic_id=t.topic_id,
                        banca=t.banca,
                        state=t.state,
                        created_at=t.created_at,
                        updated_at=t.updated_at
                    )
                    for t in threads
                ]
                
        except Exception as e:
            self.logger.error(
                "Failed to get user active sessions",
                user_id=user_id,
                error=str(e)
            )
            return []
    
    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Clean up old inactive sessions.
        
        Args:
            days: Number of days after which to clean up sessions
        
        Returns:
            Number of sessions cleaned up
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            with self.SessionLocal() as db:
                # Get old threads
                old_threads = db.query(ChatThreadModel).filter(
                    ChatThreadModel.updated_at < cutoff_date,
                    ChatThreadModel.state != "active"
                ).all()
                
                count = len(old_threads)
                
                # Delete messages first
                for thread in old_threads:
                    db.query(ChatMessageModel).filter(
                        ChatMessageModel.thread_id == thread.thread_id
                    ).delete()
                
                # Delete threads
                db.query(ChatThreadModel).filter(
                    ChatThreadModel.updated_at < cutoff_date,
                    ChatThreadModel.state != "active"
                ).delete()
                
                db.commit()
                
                self.logger.info(
                    "Cleaned up old sessions",
                    count=count,
                    cutoff_date=cutoff_date
                )
                
                return count
                
        except Exception as e:
            self.logger.error(
                "Failed to cleanup old sessions",
                error=str(e)
            )
            return 0
    
    def get_checkpointer(self) -> PostgresCheckpointSaver:
        """Get the LangGraph checkpointer instance."""
        return self.checkpointer


# Global instance
_persistence_instance = None

def get_guided_learning_persistence() -> GuidedLearningPersistence:
    """Get or create the global persistence instance."""
    global _persistence_instance
    if _persistence_instance is None:
        _persistence_instance = GuidedLearningPersistence()
    return _persistence_instance
