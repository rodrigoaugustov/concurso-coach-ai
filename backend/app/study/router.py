# Em backend/app/study/router.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.users.auth import get_current_user
from app.users.models import User
from app.contests.schemas import ContestRoleForSubscription
from . import services, schemas
from .ui_schemas import ProceduralLayout

router = APIRouter()

# === NOVOS ENDPOINTS PARA CORRIGIR BUG DE INSCRIÇÃO DUPLICADA ===

@router.get("/available-roles", response_model=List[ContestRoleForSubscription], summary="Get available roles for enrollment")
def get_available_roles(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Retorna uma lista de cargos disponíveis para inscrição,
    excluindo aqueles em que o usuário já está inscrito, com os dados do concurso (id, name).
    Ideal para o fluxo de onboarding, evitando re-inscrições acidentais.
    """
    return services.get_available_roles_for_user(db=db, user=current_user)

@router.get("/subscriptions", response_model=List[schemas.UserContestSubscription], summary="Get user subscriptions")
def get_user_subscriptions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Retorna todas as inscrições ativas do usuário logado.
    Alias conveniente para o endpoint /user-contests/.
    """
    return services.get_all_user_subscriptions(db=db, user=current_user)

# === ENDPOINTS EXISTENTES ATUALIZADOS ===

@router.post("/subscribe/{role_id}", 
            response_model=schemas.UserContestSubscription, 
            status_code=status.HTTP_201_CREATED,
            summary="Subscribe to a contest role",
            responses={
                409: {"description": "User already enrolled in this role"},
                404: {"description": "Role not found"}
            })
def subscribe_to_contest_role(
    role_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Inscreve o usuário logado em um cargo específico de um concurso.
    
    **Validações:**
    - Verifica se o cargo existe
    - Impede inscrições duplicadas (retorna 409 Conflict)
    - Inicializa o progresso em todos os tópicos do cargo
    
    **Retorna 409 Conflict se:**
    - O usuário já está inscrito neste cargo
    """
    user_contest = services.subscribe_user_to_role(db=db, user=current_user, role_id=role_id)
    return user_contest

@router.get("/user-contests/{user_contest_id}/topic-groups", response_model=List[str])
def get_subscription_topic_groups(
    user_contest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de grupos de tópicos (TopicGroup) para uma inscrição de concurso.
    O frontend usa isso para montar o formulário de autoavaliação.
    """
    return services.get_topic_groups_for_subscription(db=db, user=current_user, user_contest_id=user_contest_id)

@router.post("/user-contests/{user_contest_id}/proficiency")
def submit_proficiency_assessment(
    user_contest_id: int,
    submission: schemas.ProficiencySubmission,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Recebe a autoavaliação do usuário por MATÉRIA e replica (cascateia)
    a proficiência para todos os tópicos individuais dentro de cada matéria.
    """
    return services.update_user_proficiency_by_subject( # <-- Chama a nova função
        db=db, user=current_user, user_contest_id=user_contest_id, submission=submission
    )

@router.post("/user-contests/{user_contest_id}/generate-plan", response_model=schemas.PlanGenerationResponse)
def generate_study_plan_endpoint(
    user_contest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)    
):
    """
    Aciona a geração do roadmap de estudos personalizado pela IA.
    Isso coleta todos os dados do usuário e do concurso, envia para a IA e
    salva o plano de estudos priorizado no banco de dados.
    """
    return services.generate_study_plan(db=db, user=current_user, user_contest_id=user_contest_id)

@router.get("/user-contests/{user_contest_id}/subjects", response_model=List[str])
def get_subscription_subjects(
    user_contest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de matérias (Subjects) para uma inscrição de concurso.
    O frontend usa isso para montar o formulário de autoavaliação.
    """
    return services.get_subjects_for_subscription(db=db, user=current_user, user_contest_id=user_contest_id)

@router.get("/user-contests/{user_contest_id}/next-session", response_model=schemas.NextStudySessionResponse)
def get_next_study_session(
    user_contest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Retorna a próxima Sessão de Foco para o usuário, que consiste em:
    1. A sessão principal de estudo, baseada no roadmap da IA.
    2. Um tópico opcional para revisão rápida, baseado na repetição espaçada.
    """
    return services.get_next_session_for_user(db=db, user=current_user, user_contest_id=user_contest_id)

@router.post("/user-contests/{user_contest_id}/complete-session")
def complete_session(
    user_contest_id: int,
    completion_data: schemas.SessionCompletionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Marca uma sessão de estudo como concluída.
    Isso atualiza o progresso do usuário e agenda a próxima revisão
    para os tópicos estudados, com base na repetição espaçada.
    """
    return services.complete_study_session(
        db=db, user=current_user, user_contest_id=user_contest_id, completion_data=completion_data
    )

@router.post("/generate-layout", response_model=ProceduralLayout)
def generate_layout_endpoint(
    request: schemas.LayoutGenerationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Gera um layout de UI procedural e dinâmico para uma Sessão de Foco.
    A resposta é uma árvore de componentes JSON para o frontend renderizar.
    """
    return services.generate_procedural_layout(db=db, request=request)

@router.get("/user-contests/", response_model=List[schemas.UserContestSubscription]) 
def get_all_user_subscriptions_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Retorna todas as inscrições de concurso para o usuário logado."""
    return services.get_all_user_subscriptions(db=db, user=current_user)

@router.post("/sessions/{session_id}/generate-layout", response_model=ProceduralLayout)
def get_or_generate_layout_endpoint(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Obtém o layout da aula para uma sessão.
    Se o layout ainda não foi gerado, ele aciona a IA para criá-lo,
    salva o resultado, e o retorna. Se já existe, retorna do cache do banco.
    """
    return services.get_or_generate_layout(db=db, user=current_user, session_id=session_id)
