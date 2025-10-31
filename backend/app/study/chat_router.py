from __future__ import annotations
import json
import time
from typing import AsyncGenerator, Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage

from app.core.security import get_current_user
from app.core.database import get_db
from app.core.rate_limiting import limiter

from .chat_schemas import ChatStartRequest, ChatContinueRequest
from .agents_graph import build_study_graph
from .suggestions_service import SuggestionsService
from .ownership_service import OwnershipService
from .analytics_service import AnalyticsService
from langgraph.checkpoint.postgres import PostgresCheckpointSaver
from app.core.settings import settings
from app.core.langchain_service import LangChainService
from app.core.prompt_templates import TUTOR_SYSTEM_TEMPLATE

router = APIRouter(prefix="/api/v1/study/sessions", tags=["chat"])

_session_threads: Dict[str, Dict] = {}
_checkpointer = PostgresCheckpointSaver.from_conn_string(settings.DATABASE_URL)
_app = build_study_graph().compile(checkpointer=_checkpointer)
_suggestions = SuggestionsService()

async def sse_stream(generator: AsyncGenerator[dict, None]) -> StreamingResponse:
    async def event_source():
        async for payload in generator:
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    return StreamingResponse(event_source(), media_type="text/event-stream")

async def stream_llm_deltas(chat_history: list, topic_name: str, proficiency_level: int, banca: str | None) -> AsyncGenerator[dict, None]:
    lc = LangChainService()
    prompt = TUTOR_SYSTEM_TEMPLATE.partial(
        topic_name=topic_name,
        proficiency_level=proficiency_level,
        banca=banca or "Genérica",
    )
    chain = lc.create_chain(prompt, schema=None)

    last_human = next((m for m in reversed(chat_history) if isinstance(m, HumanMessage)), None)
    user_text = last_human.content if last_human else "Inicie a explicação do tópico."

    buffer = []
    async for chunk in chain.astream({"input": user_text, "chat_history": chat_history}):
        text = getattr(chunk, "content", None) or str(chunk)
        if text:
            buffer.append(text)
            yield {"type": "delta", "content": text}
    final_text = "".join(buffer).strip()
    if final_text:
        yield {"type": "final", "content": final_text}

@router.post("/start")
@limiter.limit("5/minute")
async def start_chat_session(payload: ChatStartRequest, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    owner = OwnershipService(db)
    uc = owner.ensure_user_contest_topic(user.id, payload.user_contest_id, payload.topic_id)
    proficiency = owner.estimate_proficiency(user.id, payload.topic_id)

    chat_id = f"t_{user.id}_{payload.user_contest_id}_{payload.topic_id}"
    _session_threads[chat_id] = {"user_id": user.id, "context": payload.model_dump()}

    initial_state = {
        "messages": [HumanMessage(content="Iniciar sessão de aprendizagem guiada.")],
        "topic_name": str(payload.topic_id),
        "proficiency_level": proficiency,
        "banca": payload.banca or "Genérica",
    }
    config = {"configurable": {"thread_id": chat_id}}

    async def gen():
        last_ai: str | None = None
        t0 = time.time()
        async for delta in stream_llm_deltas(initial_state["messages"], initial_state["topic_name"], initial_state["proficiency_level"], initial_state["banca"]):
            yield delta
        last_agent = None
        async for event in _app.astream(initial_state, config=config):
            if "messages" in event:
                msgs = event["messages"]
                if msgs and isinstance(msgs[-1], AIMessage):
                    last_ai = msgs[-1].content
                    last_agent = event.get("agent", "explanation")
                    yield {"type": "final", "content": last_ai, "agent": last_agent}
            if "suggestions" in event and event["suggestions"]:
                yield {"type": "suggestions", "content": event["suggestions"]}
        if last_ai:
            sugs = await _suggestions.generate(
                assistant_message=last_ai,
                topic_name=str(payload.topic_id),
                proficiency_level=proficiency,
                banca=payload.banca,
            )
            yield {"type": "suggestions", "content": sugs}
        duration_ms = int(round((time.time() - t0) * 1000))
        AnalyticsService(db).record(
            chat_id=chat_id,
            user_id=user.id,
            phase="start",
            duration_ms=duration_ms,
            interaction_source=None,
            agent=last_agent,
        )
        yield {"type": "done"}

    return await sse_stream(gen())

@router.post("/{chat_id}/continue")
@limiter.limit("30/minute")
async def continue_chat_session(chat_id: str, payload: ChatContinueRequest, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    thread = _session_threads.get(chat_id)
    if not thread or thread.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Chat não encontrado")

    owner = OwnershipService(db)
    ctx = thread["context"]
    uc = owner.ensure_user_contest_topic(user.id, ctx["user_contest_id"], ctx["topic_id"])
    proficiency = owner.estimate_proficiency(user.id, ctx["topic_id"])

    input_state = {
        "messages": [HumanMessage(content=payload.message)],
        "topic_name": str(ctx["topic_id"]),
        "proficiency_level": proficiency,
        "banca": ctx.get("banca") or "Genérica",
    }
    config = {"configurable": {"thread_id": chat_id}}

    async def gen():
        last_ai: str | None = None
        last_agent = None
        t0 = time.time()
        async for delta in stream_llm_deltas(input_state["messages"], input_state["topic_name"], input_state["proficiency_level"], input_state["banca"]):
            yield delta
        async for event in _app.astream(input_state, config=config):
            if "messages" in event:
                msgs = event["messages"]
                if msgs and isinstance(msgs[-1], AIMessage):
                    last_ai = msgs[-1].content
                    last_agent = event.get("agent", "explanation")
                    yield {"type": "final", "content": last_ai, "agent": last_agent}
            if "suggestions" in event and event["suggestions"]:
                yield {"type": "suggestions", "content": event["suggestions"]}
        if last_ai:
            sugs = await _suggestions.generate(
                assistant_message=last_ai,
                topic_name=str(ctx["topic_id"]),
                proficiency_level=proficiency,
                banca=ctx.get("banca"),
            )
            yield {"type": "suggestions", "content": sugs}
        duration_ms = int(round((time.time() - t0) * 1000))
        AnalyticsService(db).record(
            chat_id=chat_id,
            user_id=user.id,
            phase="continue",
            duration_ms=duration_ms,
            interaction_source=getattr(payload, "interaction_source", None),
            agent=last_agent,
        )
        yield {"type": "done"}

    return await sse_stream(gen())

@router.post("/{chat_id}/complete")
async def complete_chat_session(chat_id: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    thread = _session_threads.get(chat_id)
    if not thread or thread.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    thread["state"] = "COMPLETED"
    return {"status": "completed"}
