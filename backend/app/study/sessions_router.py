"""
API Router for Guided Learning Sessions (now with real authentication dependency).
Exposes endpoints: start, continue (SSE and non-SSE), complete, and history.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from app.users.auth import get_current_user
from ..core.logging import get_logger
from .guided_learning_service import get_guided_learning_service
from .guided_learning_schemas import ChatStartRequest, ChatContinueRequest, ChatCompleteRequest

router = APIRouter(prefix="/api/v1/study/sessions", tags=["Guided Learning Sessions"])
logger = get_logger("guided_learning_router")

@router.post("/start")
async def start_session(
    request: Request,
    request_body: ChatStartRequest, 
    current_user=Depends(get_current_user)
):
    service = get_guided_learning_service()
    return await service.start_session(current_user.id, request_body)

@router.post("/{chat_id}/continue")
async def continue_session(
    request: Request,
    chat_id: str, 
    request_body: ChatContinueRequest, 
    current_user=Depends(get_current_user)
):
    service = get_guided_learning_service()
    return await service.continue_session(current_user.id, chat_id, request_body)

@router.post("/{chat_id}/continue/stream")
async def continue_session_stream(
    request: Request,
    chat_id: str, 
    request_body: ChatContinueRequest, 
    current_user=Depends(get_current_user)
):
    service = get_guided_learning_service()
    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in service.continue_session_stream(current_user.id, chat_id, request_body):
            yield event
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.post("/{chat_id}/complete")
async def complete_session(
    chat_id: str, 
    request_body: ChatCompleteRequest, 
    current_user=Depends(get_current_user)
):
    service = get_guided_learning_service()
    return await service.complete_session(current_user.id, chat_id, request_body)

@router.get("/{chat_id}/history")
async def get_history(
    chat_id: str, 
    current_user=Depends(get_current_user)
):
    service = get_guided_learning_service()
    return await service.get_session_history(current_user.id, chat_id)
