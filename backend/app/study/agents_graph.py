from __future__ import annotations
from typing import Any, Dict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresCheckpointSaver
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field

from app.core.settings import settings
from app.core.langchain_service import LangChainService
from app.core.prompt_templates import TUTOR_SYSTEM_TEMPLATE

# Estado do grafo (padrão minimalista)
class StudyState(BaseModel):
    messages: list[Any] = Field(default_factory=list)
    topic_name: str
    proficiency_level: int
    banca: str | None = None
    suggestions: list[str] | None = None
    agent: str | None = None

# Nós/agentes simples (MVP)
async def explanation_node(state: StudyState) -> StudyState:
    # Usa template do tutor como base (poderíamos especializar por agente)
    lc = LangChainService()
    prompt = TUTOR_SYSTEM_TEMPLATE.partial(
        topic_name=state.topic_name,
        proficiency_level=state.proficiency_level,
        banca=state.banca or "Genérica",
    )
    chain = lc.create_chain(prompt, schema=None)
    # Para MVP, invocamos sem streaming e agregamos resposta
    user_last = next((m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None)
    user_text = user_last.content if user_last else "Inicie a explicação do tópico."
    ai_text = await chain.ainvoke({"input": user_text, "chat_history": state.messages})
    state.messages.append(AIMessage(content=str(ai_text)))
    # Sugestões estáticas (serão geradas pela IA posteriormente)
    state.suggestions = ["Me dê um exemplo", "Explique de outra forma", "Próximo tópico"]
    state.agent = "explanation"
    return state

# Supervisor mínimo: sempre envia para explanation (MVP)
async def supervisor_route(state: StudyState) -> str:
    return "explanation"

# Compilação do grafo com checkpointer Postgres
def build_study_graph() -> StateGraph:
    graph = StateGraph(StudyState)
    graph.add_node("explanation", explanation_node)
    graph.set_entry_point("explanation")
    graph.add_edge("explanation", END)
    return graph

# Singleton básico para reuse
_checkpointer = PostgresCheckpointSaver.from_conn_string(settings.DATABASE_URL)
_graph_app = build_study_graph().compile(checkpointer=_checkpointer)

async def ainvoke_study_graph(initial_state: Dict, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    return await _graph_app.ainvoke(initial_state, config=config)

async def astream_study_graph(input_state: Dict, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    async for event in _graph_app.astream(input_state, config=config):
        yield event
