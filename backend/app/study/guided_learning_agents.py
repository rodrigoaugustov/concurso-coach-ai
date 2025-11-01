"""
Multi-Agent Guided Learning with real AI responses.
Deterministic implementation without optional imports or fallbacks.
"""

from typing import Dict, List, Any
from enum import Enum
from langchain_core.messages import BaseMessage, HumanMessage

from ..core.ai_service import ChainFactory
from ..core.logging import get_logger
from .guided_learning_schemas import AssistantMessage, AgentResponse, SessionIntroResponse


class AgentType(str, Enum):
    EXPLANATION = "explanation"
    EXAMPLE = "example"
    QUIZ = "quiz"


class GuidedLearningAgents:
    """Deterministic multi-agent orchestrator using prompt templates and ChainFactory."""

    def __init__(self, chain_factory: ChainFactory):
        self.chain_factory = chain_factory
        self.logger = get_logger("guided_learning_agents")

    def _route(self, message: str) -> str:
        text = message.lower()
        if any(w in text for w in ["quiz", "teste", "avaliação", "questão", "exercício"]):
            return AgentType.QUIZ.value
        if any(w in text for w in ["exemplo", "prático", "aplicação", "como fazer", "situação"]):
            return AgentType.EXAMPLE.value
        return AgentType.EXPLANATION.value

    async def process_message(
        self,
        chat_id: str,
        user_id: int,
        user_message: str,
        session_context: Dict[str, Any],
        message_history: List[BaseMessage],
    ) -> AssistantMessage:
        agent = self._route(user_message)
        ctx = {
            "topic_name": session_context["topic_name"],
            "subject": session_context["subject"],
            "proficiency": int(session_context["proficiency"] * 10),
            "banca": session_context.get("banca", "Não especificada"),
            "supervisor_instructions": f"Responda como agente {agent} sobre '{user_message}'",
            # IMPORTANT: pass list[BaseMessage] to MessagesPlaceholder
            "messages": message_history + [HumanMessage(content=user_message)],
        }
        template = f"{agent}_agent"
        resp = await self.chain_factory.ainvoke(template, ctx, AgentResponse)
        return AssistantMessage(content=resp.content, ui_kind=resp.ui_kind, agent=resp.agent, suggestions=resp.suggestions or [])

    async def start_session(self, chat_id: str, session_context: Dict[str, Any]) -> AssistantMessage:
        ctx = {
            "topic_name": session_context["topic_name"],
            "subject": session_context["subject"],
            "proficiency": int(session_context["proficiency"] * 10),
            "banca": session_context.get("banca", "Não especificada"),
        }
        resp = await self.chain_factory.ainvoke("session_intro", ctx, SessionIntroResponse)
        return AssistantMessage(content=resp.content, ui_kind=resp.ui_kind, agent=resp.agent, suggestions=resp.suggestions)

    def _format_history(self, messages: List[BaseMessage]) -> str:
        # Kept for potential logging/debugging usage
        if not messages:
            return ""
        out = []
        for m in messages[-5:]:
            role = "Usuário" if isinstance(m, HumanMessage) else "Assistente"
            content = m.content[:150] + "..." if len(m.content) > 150 else m.content
            out.append(f"{role}: {content}")
        return "\n".join(out)
