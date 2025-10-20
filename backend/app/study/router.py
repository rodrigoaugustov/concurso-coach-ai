# Em backend/app/study/router.py
from typing import Annotated, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.users.auth import get_current_user
from app.users.models import User
from . import services, schemas

router = APIRouter()

@router.post("/subscribe/{role_id}", response_model=schemas.UserContestSubscription)
def subscribe_to_contest_role(
    role_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Inscreve o usuário logado em um cargo específico de um concurso.
    Isso cria o vínculo UserContest e inicializa o progresso em todos os tópicos.
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