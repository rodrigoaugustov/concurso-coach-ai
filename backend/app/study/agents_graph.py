from __future__ import annotations
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_agent_supervisor
from langchain_core.messages import HumanMessage, AIMessage

from app.core.langchain_service import LangChainService
from app.core.prompt_templates import ChatPromptTemplate, TUTOR_SYSTEM_TEMPLATE

class StudyState(BaseModel):
    messages: list[Any] = Field(default_factory=list)
    topic_name: str
    proficiency_level: int
    banca: Optional[str] = None
    suggestions: Optional[list[str]] = None
    agent: Optional[str] = None

# Define agentes especializados com prompts distintos
def build_agents(lc: LangChainService):
    explanation_prompt = ChatPromptTemplate.from_messages([
        ("system", "Explique o conceito claramente, em linguagem acessível e com exemplos curtos."),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
    ])
    example_prompt = ChatPromptTemplate.from_messages([
        ("system", "Gere um exemplo prático e contextualizado ao concurso, passo a passo e conciso."),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
    ])
    quiz_prompt = ChatPromptTemplate.from_messages([
        ("system", "Crie 3 questões de múltipla escolha (A-D) com gabarito, concisas e alinhadas ao tópico."),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
    ])

    return {
        "explanation": lc.create_chain(explanation_prompt, schema=None),
        "example": lc.create_chain(example_prompt, schema=None),
        "quiz": lc.create_chain(quiz_prompt, schema=None),
    }

# Supervisor LLM que decide qual agente chamar
def build_supervisor(lc: LangChainService):
    system_prompt = (
        "Você é um supervisor que decide qual agente deve responder: 'explanation', 'example' ou 'quiz'. "
        "Baseie-se no último input do usuário e no contexto do chat. Responda somente com o nome do agente."
    )
    return create_agent_supervisor(agents=["explanation", "example", "quiz"], system_prompt=system_prompt)

# Grafo com supervisor LLM
def build_study_graph() -> StateGraph:
    lc = LangChainService()
    chains = build_agents(lc)
    supervisor = build_supervisor(lc)

    def node_fn(agent_name: str):
        async def _run(state: StudyState) -> StudyState:
            # Monta input combinando contexto tutor + mensagem
            last_human = next((m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None)
            user_text = last_human.content if last_human else "Inicie a explicação do tópico."
            prompt_input = {
                "input": f"Tópico: {state.topic_name} | Banca: {state.banca or 'Genérica'} | Nível: {state.proficiency_level}/10\n\n{user_text}",
                "chat_history": state.messages,
            }
            ai_resp = await chains[agent_name].ainvoke(prompt_input)
            content = getattr(ai_resp, "content", None) or str(ai_resp)
            state.messages.append(AIMessage(content=content))
            state.agent = agent_name
            return state
        return _run

    # Monta grafo
    graph = StateGraph(StudyState)
    graph.add_node("explanation", node_fn("explanation"))
    graph.add_node("example", node_fn("example"))
    graph.add_node("quiz", node_fn("quiz"))

    # Encaminhamento por supervisor (LLM)
    async def route(state: StudyState) -> str:
        last_human = next((m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None)
        msg = last_human.content if last_human else "Iniciar"
        decision = await supervisor.ainvoke({"messages": [HumanMessage(content=msg)]})
        # Normaliza saída do supervisor
        agent = str(decision).strip().lower()
        return agent if agent in {"explanation", "example", "quiz"} else "explanation"

    graph.add_conditional_edges("explanation", route, {"explanation": "explanation", "example": "example", "quiz": "quiz"})
    graph.add_conditional_edges("example", route, {"explanation": "explanation", "example": "example", "quiz": "quiz"})
    graph.add_conditional_edges("quiz", route, {"explanation": "explanation", "example": "example", "quiz": "quiz"})

    graph.set_entry_point("explanation")
    return graph
