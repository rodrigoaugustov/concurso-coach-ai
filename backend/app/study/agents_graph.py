from __future__ import annotations
from typing import Any, Dict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field

from app.core.langchain_service import LangChainService
from app.core.prompt_templates import TUTOR_SYSTEM_TEMPLATE

class StudyState(BaseModel):
    messages: list[Any] = Field(default_factory=list)
    topic_name: str
    proficiency_level: int
    banca: str | None = None
    suggestions: list[str] | None = None
    agent: str | None = None

async def explanation_node(state: StudyState) -> StudyState:
    lc = LangChainService()
    prompt = TUTOR_SYSTEM_TEMPLATE.partial(
        topic_name=state.topic_name,
        proficiency_level=state.proficiency_level,
        banca=state.banca or "Genérica",
    )
    chain = lc.create_chain(prompt, schema=None)

    # Emitir deltas via mensagens artificiais: concatenamos conteúdo em AIMessage
    user_last = next((m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None)
    user_text = user_last.content if user_last else "Inicie a explicação do tópico."
    ai_text = await chain.ainvoke({"input": user_text, "chat_history": state.messages})

    # Normaliza resposta para string
    content = getattr(ai_text, "content", None) or str(ai_text)
    state.messages.append(AIMessage(content=content))

    # Sugestões derivadas simples (fallback). Futuro: chain dedicada
    state.suggestions = [
        "Me dê um exemplo",
        "Explique de outra forma",
        "Próximo tópico",
    ]
    state.agent = "explanation"
    return state

async def example_node(state: StudyState) -> StudyState:
    lc = LangChainService()
    prompt = TUTOR_SYSTEM_TEMPLATE.partial(
        topic_name=state.topic_name,
        proficiency_level=state.proficiency_level,
        banca=state.banca or "Genérica",
    )
    chain = lc.create_chain(prompt, schema=None)
    user_last = next((m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None)
    ask = (user_last.content if user_last else "") + "\nForneça um exemplo prático curto."
    ai_text = await chain.ainvoke({"input": ask, "chat_history": state.messages})
    content = getattr(ai_text, "content", None) or str(ai_text)
    state.messages.append(AIMessage(content=content))
    state.suggestions = ["Explique de outra forma", "Quiz rápido", "Próximo tópico"]
    state.agent = "example"
    return state

async def quiz_node(state: StudyState) -> StudyState:
    lc = LangChainService()
    prompt = TUTOR_SYSTEM_TEMPLATE.partial(
        topic_name=state.topic_name,
        proficiency_level=state.proficiency_level,
        banca=state.banca or "Genérica",
    )
    chain = lc.create_chain(prompt, schema=None)
    ask = "Gere 3 perguntas de múltipla escolha (A-D) com gabarito ao final no formato JSON simples."
    ai_text = await chain.ainvoke({"input": ask, "chat_history": state.messages})
    content = getattr(ai_text, "content", None) or str(ai_text)
    state.messages.append(AIMessage(content=content))
    state.suggestions = ["Responder quiz", "Explicar novamente", "Próximo tópico"]
    state.agent = "quiz"
    return state

async def supervisor_route(state: StudyState) -> str:
    # Heurística simples para MVP
    last_human = next((m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None)
    text = (last_human.content.lower() if last_human else "")
    if any(k in text for k in ["exemplo", "example"]):
        return "example"
    if any(k in text for k in ["quiz", "pergunta", "avaliar"]):
        return "quiz"
    return "explanation"

def build_study_graph() -> StateGraph:
    graph = StateGraph(StudyState)
    graph.add_node("explanation", explanation_node)
    graph.add_node("example", example_node)
    graph.add_node("quiz", quiz_node)

    graph.add_conditional_edges(
        "explanation",
        supervisor_route,
        {"explanation": "explanation", "example": "example", "quiz": "quiz"},
    )
    graph.add_conditional_edges(
        "example",
        supervisor_route,
        {"explanation": "explanation", "example": "example", "quiz": "quiz"},
    )
    graph.add_conditional_edges(
        "quiz",
        supervisor_route,
        {"explanation": "explanation", "example": "example", "quiz": "quiz"},
    )

    # Terminar após um passo (MVP); em breve, condicionaremos pelo estado
    graph.add_edge("explanation", END)
    graph.add_edge("example", END)
    graph.add_edge("quiz", END)
    graph.set_entry_point("explanation")
    return graph
