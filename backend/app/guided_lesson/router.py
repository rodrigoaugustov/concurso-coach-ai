
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from langchain_google_genai import ChatGoogleGenerativeAI
import json

from app.core.database import get_db
from app.users.auth import get_current_user
from app.users import schemas as user_schemas
from app.core.settings import settings
from app.study.schemas import StudySession
from . import crud, schemas, models
from .agents import StudySessionAgent, LessonSessionContext

router = APIRouter()

@router.post("/start", response_model=schemas.LessonStartResponse, status_code=status.HTTP_201_CREATED)
def start_guided_lesson(
    request: StudySession,
    db: Session = Depends(get_db),
    current_user: user_schemas.User = Depends(get_current_user),
):
    """Inicia uma nova sessão de aula guiada."""

    session_id = request.session_id

    # Create context for the agent
    ctx = LessonSessionContext(
        session_id=session_id,
        user_id=current_user.id,
        topics=request.topics,
    )

    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, api_key=settings.GEMINI_API_KEY)
    agent = StudySessionAgent(model).start_agent()

    # Converte a lista de tópicos em uma string para o prompt inicial
    topicos = ", ".join(f"{t.subject}: {t.topic}" for t in request.topics)
    
    initial_content = f"Vamos iniciar a sessão de estudo guiada. O conteúdo dessa será será sobre: '{topicos}'. Por favor, comece a aula guiada."
    
    res = agent.invoke({
        "messages": [{"role": "user", "content": initial_content}]
        }, context=ctx, config={"configurable": {"thread_id": f"guided_lesson_{session_id}"}})
    
    initial_message = json.dumps(res["messages"][-1].content)

    crud.add_message_to_history(
        db=db,
        session_id=session_id,
        sender_type=models.SenderType.AI,
        content=initial_message
    )

    return {"session_id": session_id, "message": initial_message}

@router.post("/{session_id}/chat", response_model=schemas.ChatMessageResponse)
def handle_chat_message(
    session_id: int,
    request: schemas.ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: user_schemas.User = Depends(get_current_user),
):
    """Processa uma mensagem do usuário e retorna a resposta do agente."""
    # 1. Salvar mensagem do usuário
    crud.add_message_to_history(
        db=db,
        session_id=session_id,
        sender_type=models.SenderType.USER,
        content=request.content
    )

    # 2. Construir contexto e histórico para o agente
    ctx = LessonSessionContext(
        session_id=session_id,
        user_id=current_user.id,
        topics=request.session_contents.topics
    )
    
    # 3. Chamar o agente
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, api_key=settings.GEMINI_API_KEY)
    agent = StudySessionAgent(model).start_agent()
    input_messages = {"messages": [{"role": "user", "content": request.content}]}
    res = agent.invoke(
        input_messages,
        context=ctx, 
        config={"configurable": {"thread_id": f"guided_lesson_{session_id}"}}
    )
    
    agent_response_content = json.dumps(res["messages"][-1].content)

    # 4. Salvar resposta do agente
    crud.add_message_to_history(
        db=db,
        session_id=session_id,
        sender_type=models.SenderType.AI,
        content=agent_response_content
    )

    # 5. Retornar a resposta e o histórico atualizado
    updated_history = crud.get_full_conversation_history(db, session_id=session_id)
    
    return {"agent_response": agent_response_content, "history": updated_history}

@router.get("/{session_id}/history", response_model=list[schemas.MessageHistoryInDB])
def get_chat_history(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: user_schemas.User = Depends(get_current_user),
):
    """Retorna o histórico de mensagens de uma sessão de aula guiada."""
    # TODO: Add validation to ensure the user has access to this session
    history = crud.get_full_conversation_history(db, session_id=session_id)
    return history