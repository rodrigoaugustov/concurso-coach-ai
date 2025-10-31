from __future__ import annotations
import json
from typing import AsyncGenerator, Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage

from app.core.security import get_current_user
from app.core.database import get_db

from .chat_schemas import ChatStartRequest, ChatContinueRequest
from .agents_graph import build_study_graph
from langgraph.checkpoint.postgres import PostgresCheckpointSaver
from app.core.settings import settings

router = APIRouter(prefix="/api/v1/study/sessions", tags=["chat"])

_session_threads: Dict[str, Dict] = {}
_checkpointer = PostgresCheckpointSaver.from_conn_string(settings.DATABASE_URL)
_app = build_study_graph().compile(checkpointer=_checkpointer)

async def sse_stream(generator: AsyncGenerator[dict, None]) -> StreamingResponse:
    async def event_source():
        async for payload in generator:
            yield f"data: {json.dumps(payload)}\n\n"
    return StreamingResponse(event_source(), media_type="text/event-stream")

@router.post("/start")
async def start_chat_session(payload: ChatStartRequest, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    chat_id = f"t_{user.id}_{payload.user_contest_id}_{payload.topic_id}"
    _session_threads[chat_id] = {"user_id": user.id, "context": payload.model_dump()}

    initial_state = {
        "messages": [HumanMessage(content="Iniciar sessão de aprendizagem guiada.")],
        "topic_name": str(payload.topic_id),
        "proficiency_level": 5,
        "banca": payload.banca or "Genérica",
    }
    config = {"configurable": {"thread_id": chat_id}}

    async def gen():
        async for event in _app.astream(initial_state, config=config):
            # Mapear eventos do LangGraph para SSE
            if "messages" in event:  # estado parcial/final
                msgs = event["messages"]
                if msgs and isinstance(msgs[-1], AIMessage):
                    yield {"type": "final", "content": msgs[-1].content, "agent": event.get("agent", "explanation")}
            if "suggestions" in event and event["suggestions"]:
                yield {"type": "suggestions", "content": event["suggestions"]}
        # Garantir término
        yield {"type": "done"}

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
    config = {"configurable": {"thread_id": chat_id}}

    async def gen():
        async for event in _app.astream(input_state, config=config):
            if "messages" in event:
                msgs = event["messages"]
                if msgs and isinstance(msgs[-1], AIMessage):
                    yield {"type": "final", "content": msgs[-1].content, "agent": event.get("agent", "explanation")}
            if "suggestions" in event and event["suggestions"]:
                yield {"type": "suggestions", "content": event["suggestions"]}
        yield {"type": "done"}

    return await sse_stream(gen())

@router.post("/{chat_id}/complete")
async def complete_chat_session(chat_id: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    thread = _session_threads.get(chat_id)
    if not thread or thread.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    thread["state"] = "COMPLETED"
    return {"status": "completed"}
