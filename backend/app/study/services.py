# Em backend/app/study/services.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from app.users.models import User, UserContest, UserTopicProgress
from app.contests.models import ContestRole, ProgrammaticContent, PublishedContest, ContestStatus
from app.core.settings import settings
from app.core.ai_service import LangChainService
from .schemas import ProficiencySubmission, SessionCompletionRequest, LayoutGenerationRequest
from .ui_schemas import ProceduralLayout
from app.users.models import AssessmentType, ProficiencyHistory
from .models import StudyRoadmapSession, roadmap_session_topics
from .plan_generator import StudyPlanGenerator
from .prompts import procedural_layout_prompt
from pydantic import TypeAdapter

# --- LÓGICA DE REPETIÇÃO ESPAÇADA ---
SPACED_REPETITION_INTERVALS = [1, 3, 7, 14, 30, 60]


def subscribe_user_to_role(db: Session, user: User, role_id: int):
    role = db.query(ContestRole).filter(ContestRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_subscription = db.query(UserContest).filter(
        UserContest.user_id == user.id,
        UserContest.contest_role_id == role_id
    ).first()
    
    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=f"Usuário já está inscrito no cargo '{role.job_title}' deste concurso."
        )

    new_user_contest = UserContest(user_id=user.id, contest_role_id=role_id)
    db.add(new_user_contest)
    db.flush()

    for topic in role.programmatic_content:
        progress = UserTopicProgress(
            user_contest_id=new_user_contest.id,
            programmatic_content_id=topic.id,
            current_proficiency_score=0.0
        )
        db.add(progress)
    
    db.commit()
    db.refresh(new_user_contest)
    return new_user_contest

def get_available_roles_for_user(db: Session, user: User):
    """
    Retorna cargos disponíveis ao usuário com o concurso aninhado (id e name),
    excluindo cargos já inscritos e considerando concursos COMPLETED.
    """
    enrolled_role_ids = db.query(UserContest.contest_role_id).filter(
        UserContest.user_id == user.id
    ).subquery()

    available_roles = (
        db.query(ContestRole)
        .options(joinedload(ContestRole.contest))
        .join(PublishedContest, ContestRole.published_contest_id == PublishedContest.id)
        .filter(
            PublishedContest.status == ContestStatus.COMPLETED,
            ~ContestRole.id.in_(enrolled_role_ids)
        )
        .order_by(PublishedContest.name, ContestRole.job_title)
        .all()
    )

    return available_roles

def get_user_enrolled_roles(db: Session, user: User):
    enrolled_subscriptions = db.query(UserContest).options(
        joinedload(UserContest.role).joinedload(ContestRole.contest)
    ).filter(
        UserContest.user_id == user.id
    ).order_by(
        UserContest.id.desc()
    ).all()
    
    return enrolled_subscriptions

# ... (demais funções inalteradas) ...
