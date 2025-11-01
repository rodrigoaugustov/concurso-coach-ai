"""
API Router for Guided Learning Sessions.
Exposes endpoints: start, continue (SSE and non-SSE), complete, and history.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from ..core.security import get_current_user
from ..core.logging import get_logger
from .guided_learning_service import get_guided_learning_service
from .guided_learning_schemas import (
    ChatStartRequest,
    ChatContinueRequest,
    ChatCompleteRequest
)

# Rate limiting setup
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    
    def get_user_id_for_rate_limit(request: Request):
        """Get user ID for rate limiting continue endpoints."""
        try:
            # Try to get user from dependencies (if already resolved)
            user = getattr(request.state, 'current_user', None)
            if user:
                return f"user_{user.id}"
        except:
            pass
        
        # Fallback to IP for anonymous requests
        return get_remote_address(request)
    
    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    limiter = None
    RATE_LIMIT_AVAILABLE = False

router = APIRouter(prefix="/api/v1/study/sessions", tags=["Guided Learning Sessions"])
logger = get_logger("guided_learning_router")

# Add rate limiter to FastAPI app if available
if RATE_LIMIT_AVAILABLE:
    logger.info("Rate limiting enabled for guided learning endpoints")
else:
    logger.warning("Rate limiting not available for guided learning endpoints")


if RATE_LIMIT_AVAILABLE:
    @router.post("/start")
    @limiter.limit("5/minute")  # 5 starts per minute per IP
    async def start_session(
        request: Request,
        request_body: ChatStartRequest, 
        current_user=Depends(get_current_user)
    ):
        """Start a new guided learning session."""
        service = get_guided_learning_service()
        return await service.start_session(current_user.id, request_body)
else:
    @router.post("/start")
    async def start_session(
        request_body: ChatStartRequest, 
        current_user=Depends(get_current_user)
    ):
        """Start a new guided learning session."""
        service = get_guided_learning_service()
        return await service.start_session(current_user.id, request_body)


if RATE_LIMIT_AVAILABLE:
    @router.post("/{chat_id}/continue")
    @limiter.limit("30/minute", key_func=get_user_id_for_rate_limit)  # 30 continues per minute per user
    async def continue_session(
        request: Request,
        chat_id: str, 
        request_body: ChatContinueRequest, 
        current_user=Depends(get_current_user)
    ):
        """Continue a chat session with regular response."""
        service = get_guided_learning_service()
        return await service.continue_session(current_user.id, chat_id, request_body)
else:
    @router.post("/{chat_id}/continue")
    async def continue_session(
        chat_id: str, 
        request_body: ChatContinueRequest, 
        current_user=Depends(get_current_user)
    ):
        """Continue a chat session with regular response."""
        service = get_guided_learning_service()
        return await service.continue_session(current_user.id, chat_id, request_body)


if RATE_LIMIT_AVAILABLE:
    @router.post("/{chat_id}/continue/stream")
    @limiter.limit("20/minute", key_func=get_user_id_for_rate_limit)  # 20 stream requests per minute per user
    async def continue_session_stream(
        request: Request,
        chat_id: str, 
        request_body: ChatContinueRequest, 
        current_user=Depends(get_current_user)
    ):
        """Continue a chat session with streaming response (SSE)."""
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
else:
    @router.post("/{chat_id}/continue/stream")
    async def continue_session_stream(
        chat_id: str, 
        request_body: ChatContinueRequest, 
        current_user=Depends(get_current_user)
    ):
        """Continue a chat session with streaming response (SSE)."""
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
    """Complete a chat session and update progress."""
    service = get_guided_learning_service()
    return await service.complete_session(current_user.id, chat_id, request_body)


@router.get("/{chat_id}/history")
async def get_history(
    chat_id: str, 
    current_user=Depends(get_current_user)
):
    """Get chat session history and metadata."""
    service = get_guided_learning_service()
    return await service.get_session_history(current_user.id, chat_id)


# Add rate limit error handler if available
if RATE_LIMIT_AVAILABLE:
    @router.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        response = HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {exc.detail}"
        )
        logger.warning(
            "Rate limit exceeded",
            endpoint=request.url.path,
            user_agent=request.headers.get("user-agent"),
            remote_addr=get_remote_address(request)
        )
        return response
