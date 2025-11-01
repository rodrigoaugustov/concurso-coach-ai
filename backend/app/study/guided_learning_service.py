"""
Main Guided Learning Service.
Orchestrates multi-agents, persistence, streaming, and session management.
"""

from typing import Dict, List, Any, Optional, AsyncGenerator
from fastapi import HTTPException
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy.orm import Session
import asyncio
from datetime import datetime

from ..core.ai_service import ChainFactory
from ..core.logging import get_logger
from ..core.settings import get_settings
from ..core.database import get_db
from ..users.models import UserContest, UserTopicProgress
from ..contests.models import ProgrammaticContent
from .guided_learning_agents import GuidedLearningAgents, AgentType as AT
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
    DeltaEvent,
    FinalEvent,
    SuggestionsEvent,
    ErrorEvent,
)


class GuidedLearningService:
    def __init__(self):
        self.logger = get_logger("guided_learning_service")
        self.settings = get_settings()
        # Mantém o modelo gemini-2.5-flash conforme commit do usuário
        self.chain_factory = ChainFactory(
            provider="google",
            api_key=self.settings.gemini_api_key,
            model_name="gemini-2.5-flash",
            temperature=0.3,
        )
        self.agents = GuidedLearningAgents(self.chain_factory)
        self.persistence = get_guided_learning_persistence()

    async def start_session(self, user_id: int, request: ChatStartRequest) -> ChatStartResponse:
        self.logger.info("Starting guided learning session", user_id=user_id, user_contest_id=request.user_contest_id, topic_id=request.topic_id)
        try:
            session_context = await self._validate_and_get_context(user_id, request.user_contest_id, request.topic_id)
            session_context["banca"] = request.banca
            chat_id, thread_id = await self.persistence.create_chat_session(
                user_id=user_id,
                user_contest_id=request.user_contest_id,
                topic_id=request.topic_id,
                topic_name=session_context["topic_name"],
                subject=session_context["subject"],
                proficiency=session_context["proficiency"],
                banca=request.banca,
            )
            first_message = await self.agents.start_session(chat_id, session_context)
            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="assistant",
                content=first_message.content,
                ui_kind=first_message.ui_kind,
                agent=first_message.agent,
                suggestions=first_message.suggestions,
            )
            return ChatStartResponse(chat_id=chat_id, first_message=first_message)
        except Exception as e:
            self.logger.error("Failed to start session", user_id=user_id, error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to start learning session: {str(e)}")

    async def continue_session(self, user_id: int, chat_id: str, request: ChatContinueRequest) -> ChatContinueResponse:
        self.logger.info("Continuing chat session", user_id=user_id, chat_id=chat_id, message_length=len(request.message))
        try:
            session = await self.persistence.get_chat_session(chat_id)
            if not session or session.user_id != user_id:
                raise HTTPException(status_code=404, detail="Session not found")
            if session.status != "active":
                raise HTTPException(status_code=400, detail="Session is not active")

            session_context = {"topic_name": session.topic_name, "subject": session.subject, "proficiency": session.proficiency, "banca": session.banca}
            thread_id = f"chat_{chat_id}"
            message_history = await self.persistence.get_thread_history(thread_id)

            await self.persistence.save_message(chat_id=chat_id, thread_id=thread_id, role="user", content=request.message, interaction_source=request.interaction_source)

            assistant_message = await self.agents.process_message(
                chat_id=chat_id,
                user_id=user_id,
                user_message=request.message,
                session_context=session_context,
                message_history=message_history,
            )

            await self.persistence.save_message(
                chat_id=chat_id,
                thread_id=thread_id,
                role="assistant",
                content=assistant_message.content,
                ui_kind=assistant_message.ui_kind,
                agent=assistant_message.agent,
                suggestions=assistant_message.suggestions,
            )
            return ChatContinueResponse(message=assistant_message)
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error("Failed to continue session", user_id=user_id, chat_id=chat_id, error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to continue session: {str(e)}")

    async def continue_session_stream(self, user_id: int, chat_id: str, request: ChatContinueRequest) -> AsyncGenerator[str, None]:
        self.logger.info("Starting streaming session continue", user_id=user_id, chat_id=chat_id)
        try:
            session = await self.persistence.get_chat_session(chat_id)
            if not session or session.user_id != user_id:
                yield f"data: {ErrorEvent(error='Session not found', error_code='SESSION_NOT_FOUND').json()}\n\n"; return
            if session.status != "active":
                yield f"data: {ErrorEvent(error='Session is not active', error_code='SESSION_INACTIVE').json()}\n\n"; return

            session_context = {"topic_name": session.topic_name, "subject": session.subject, "proficiency": session.proficiency, "banca": session.banca}
            thread_id = f"chat_{chat_id}"
            message_history = await self.persistence.get_thread_history(thread_id)
            await self.persistence.save_message(chat_id=chat_id, thread_id=thread_id, role="user", content=request.message, interaction_source=request.interaction_source)

            agent_type = self._simple_route(request.message)
            stream_context = {
                "topic_name": session_context["topic_name"],
                "subject": session_context["subject"],
                "proficiency": int(session_context["proficiency"] * 10),
                "banca": session_context.get("banca", "Não especificada"),
                "supervisor_instructions": f"Responda como agente {agent_type} sobre '{request.message}'",
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
                assistant_message = await self.agents.process_message(chat_id, user_id, request.message, session_context, message_history)
                accumulated_content = assistant_message.content
                for i in range(0, len(accumulated_content), 25):
                    yield f"data: {DeltaEvent(content=accumulated_content[i:i+25]).json()}\n\n"
                await self.persistence.save_message(chat_id=chat_id, thread_id=thread_id, role="assistant", content=accumulated_content, ui_kind=assistant_message.ui_kind, agent=assistant_message.agent, suggestions=assistant_message.suggestions)
                yield f"data: {FinalEvent(message=assistant_message).json()}\n\n"
                yield f"data: {SuggestionsEvent(suggestions=assistant_message.suggestions).json()}\n\n"
                return

            suggestions_map = {
                AT.EXPLANATION.value: ["Pode dar um exemplo prático?", "Como isso aparece nas provas?", "Quais são os principais erros?"],
                AT.EXAMPLE.value: ["Explique o passo a passo", "Mostre outro exemplo", "Vamos praticar?"],
                AT.QUIZ.value: ["Explique a resposta", "Outra questão similar", "Como melhorar?"],
            }
            suggestions = suggestions_map.get(agent_type, suggestions_map[AT.EXPLANATION.value])

            final_message = AssistantMessage(content=accumulated_content, ui_kind=agent_type if agent_type in ["explanation", "example", "quiz"] else "explanation", agent=agent_type, suggestions=suggestions)
            yield f"data: {FinalEvent(message=final_message).json()}\n\n"
            yield f"data: {SuggestionsEvent(suggestions=suggestions).json()}\n\n"
            await self.persistence.save_message(chat_id=chat_id, thread_id=thread_id, role="assistant", content=accumulated_content, ui_kind=final_message.ui_kind, agent=final_message.agent, suggestions=suggestions)
            self.logger.info("Real streaming session completed", chat_id=chat_id, agent=agent_type, content_length=len(accumulated_content))
        except Exception as e:
            self.logger.error("Streaming session failed", user_id=user_id, chat_id=chat_id, error=str(e))
            yield f"data: {ErrorEvent(error=str(e), error_code='PROCESSING_ERROR').json()}\n\n"

    def _simple_route(self, message: str) -> str:
        text = message.lower()
        if any(w in text for w in ["quiz", "teste", "avaliação", "questão", "exercício", "praticar", "treinar", "avaliar", "verificar"]):
            return "quiz"
        if any(w in text for w in ["exemplo", "prático", "aplicação", "como fazer", "na prática", "caso real", "situação", "demonstre", "mostre"]):
            return "example"
        return "explanation"

    async def _validate_and_get_context(self, user_id: int, user_contest_id: int, topic_id: int) -> Dict[str, Any]:
        db: Session = next(get_db())
        try:
            uc = db.query(UserContest).filter(UserContest.id == user_contest_id, UserContest.user_id == user_id).first()
            if not uc:
                raise HTTPException(status_code=404, detail="User contest not found or access denied")
            topic = db.query(ProgrammaticContent).filter(ProgrammaticContent.id == topic_id, ProgrammaticContent.contest_role_id == uc.contest_role_id).first()
            if not topic:
                raise HTTPException(status_code=404, detail="Topic not found in this contest")
            prog = db.query(UserTopicProgress).filter(UserTopicProgress.user_contest_id == user_contest_id, UserTopicProgress.programmatic_content_id == topic_id).first()
            if not prog:
                from app.users.models import UserTopicProgress as Prog
                prog = Prog(user_contest_id=user_contest_id, programmatic_content_id=topic_id, current_proficiency_score=0.3, sessions_studied=0)
                db.add(prog); db.commit(); db.refresh(prog)
            return {"topic_name": topic.topic, "subject": topic.subject, "exam_module": topic.exam_module, "proficiency": prog.current_proficiency_score, "sessions_studied": prog.sessions_studied}
        finally:
            db.close()
