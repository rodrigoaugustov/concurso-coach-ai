from __future__ import annotations
from typing import AsyncGenerator, Dict
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.security import get_current_user  # assume existente
from app.core.database import get_db  # assume existente
from app.core.langchain_service import LangChainService
from app.core.prompt_templates import TUTOR_SYSTEM_TEMPLATE

from .chat_schemas import ChatStartRequest, ChatContinueRequest

router = APIRouter(prefix="/api/v1/study/sessions", tags=["chat"])

# Placeholder simples para state; será trocado por LangGraph checkpointer
_session_threads: Dict[str, Dict] = {}

async def sse_wrap(generator: AsyncGenerator[str, None]) -> StreamingResponse:
    async def event_source():
        async for chunk in generator:
            yield f"data: {chunk}\n\n"
    return StreamingResponse(event_source(), media_type="text/event-stream")

@router.post("/start")
async def start_chat_session(payload: ChatStartRequest, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # TODO: validar user_contest_id/topic_id pertencem ao usuário
    chat_id = f"t_{user.id}_{payload.user_contest_id}_{payload.topic_id}"

    lc = LangChainService()
    # Partial do template com contexto inicial
    prompt = TUTOR_SYSTEM_TEMPLATE.partial(
        topic_name=str(payload.topic_id),
        proficiency_level=5,  # TODO: calcular pela base
        banca=payload.banca or "Genérica",
    )
    chain = lc.create_chain(prompt, schema=None)

    async def gen():
        # Usaremos astream quando adicionarmos LangGraph/LLM com suporte a streaming
        # Por ora, devolve um único bloco JSON básico simulando delta
        first_msg = {
            "type": "final",
            "content": "Bem-vindo! Vamos começar com uma visão geral do tópico. O que você já sabe sobre isso?",
        }
        yield json.dumps(first_msg)
        suggestions = {"type": "suggestions", "content": ["Continue", "Me dê um exemplo", "Explique de outra forma"]}
        yield json.dumps(suggestions)

    _session_threads[chat_id] = {"user_id": user.id, "context": payload.model_dump()}
    return await sse_wrap(gen())

@router.post("/{chat_id}/continue")
async def continue_chat_session(chat_id: str, payload: ChatContinueRequest, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    thread = _session_threads.get(chat_id)
    if not thread or thread.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Chat não encontrado")

    lc = LangChainService()
    prompt = TUTOR_SYSTEM_TEMPLATE.partial(
        topic_name=str(thread["context"]["topic_id"]),
        proficiency_level=5,
        banca=thread["context"].get("banca") or "Genérica",
    )
    chain = lc.create_chain(prompt, schema=None)

    async def gen():
        # Simulação de resposta em partes
        deltas = [
            {"type": "delta", "content": "Vamos aprofundar: "},
            {"type": "delta", "content": "conceito-chave -> "},
            {"type": "delta", "content": "princípio da legalidade."},
        ]
        for d in deltas:
            yield json.dumps(d)
        final = {"type": "final", "content": "Isso faz sentido? Quer ver um exemplo prático ou avançar?"}
        yield json.dumps(final)
        suggestions = {"type": "suggestions", "content": ["Me dê um exemplo", "Explique de outra forma", "Próximo tópico"]}
        yield json.dumps(suggestions)

    return await sse_wrap(gen())

@router.post("/{chat_id}/complete")
async def complete_chat_session(chat_id: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    thread = _session_threads.get(chat_id)
    if not thread or thread.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    thread["state"] = "COMPLETED"
    # TODO: integrar com agendamento de revisão e progresso
    return {"status": "completed"}
