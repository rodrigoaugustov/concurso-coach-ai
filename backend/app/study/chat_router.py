from __future__ import annotations
import json
from typing import AsyncGenerator, Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage

from app.core.security import get_current_user
from app.core.database import get_db

from .chat_schemas import ChatStartRequest, ChatContinueRequest
from .agents_graph import ainvoke_study_graph, astream_study_graph

router = APIRouter(prefix="/api/v1/study/sessions", tags=["chat"])

_session_threads: Dict[str, Dict] = {}

async def sse_stream(generator: AsyncGenerator[dict, None]) -> StreamingResponse:
    async def event_source():
        async for payload in generator:
            yield f"data: {json.dumps(payload)}\n\n"
    return StreamingResponse(event_source(), media_type="text/event-stream")

@router.post("/start")
async def start_chat_session(payload: ChatStartRequest, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # TODO: validar vínculo user_contest/topic
    chat_id = f"t_{user.id}_{payload.user_contest_id}_{payload.topic_id}"
    _session_threads[chat_id] = {"user_id": user.id, "context": payload.model_dump()}

    initial_state = {
        "messages": [HumanMessage(content="Iniciar sessão de aprendizagem guiada.")],
        "topic_name": str(payload.topic_id),
        "proficiency_level": 5,
        "banca": payload.banca or "Genérica",
    }

    async def gen():
        # Stream de eventos do LangGraph
        async for _ in astream_study_graph(initial_state, thread_id=chat_id):
            # Para MVP: emitir apenas evento final fabricado
            # (LangGraph astream retorna frames internos; aqui encapsulamos)
            pass
        yield {"type": "final", "content": "Bem-vindo! Vamos começar com uma visão geral do tópico.", "agent": "explanation"}
        yield {"type": "suggestions", "content": ["Continue", "Me dê um exemplo", "Explique de outra forma"]}

    return await sse_stream(gen())

@router.post("/{chat_id}/continue")
async def continue_chat_session(chat_id: str, payload: ChatContinueRequest, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    thread = _session_threads.get(chat_id)
    if not thread or thread.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Chat não encontrado")

    input_state = {
        "messages": [HumanMessage(content=payload.message)],
        "topic_name": str(thread["context"]["topic_id"]),
        "proficiency_level": 5,
        "banca": thread["context"].get("banca") or "Genérica",
    }

    async def gen():
        # Stream de eventos do LangGraph
        async for _ in astream_study_graph(input_state, thread_id=chat_id):
            pass
        yield {"type": "delta", "content": "Vamos aprofundar: "}
        yield {"type": "delta", "content": "conceito-chave -> "}
        yield {"type": "final", "content": "princípio da legalidade. Isso faz sentido?"}
        yield {"type": "suggestions", "content": ["Me dê um exemplo", "Explique de outra forma", "Próximo tópico"]}

    return await sse_stream(gen())

@router.post("/{chat_id}/complete")
async def complete_chat_session(chat_id: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    thread = _session_threads.get(chat_id)
    if not thread or thread.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    thread["state"] = "COMPLETED"
    return {"status": "completed"}
