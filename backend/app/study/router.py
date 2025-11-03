from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.users.auth import get_current_user
from app.users.models import User
from app.contests.schemas import ContestRoleForSubscription
from . import services, schemas
from .ui_schemas import ProceduralLayout
from app.core.security import InputValidator

# Rate limiting (decorator) - optional if slowapi available
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
except Exception:
    limiter = None

router = APIRouter()

# Helper: validate numeric IDs
def _ensure_valid_id(value: int, name: str = "id"):
    if not InputValidator.validate_numeric_id(value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {name}")

# Rate limit 2/min per IP (can be adapted later to per-user key)
limit_generate_plan = (limiter.limit("2/minute") if limiter else (lambda f: f))


@router.get("/available-roles", response_model=List[ContestRoleForSubscription], summary="Get available roles for enrollment")
def get_available_roles(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    return services.get_available_roles_for_user(db=db, user=current_user)


@router.get("/subscriptions", response_model=List[schemas.UserContestSubscription], summary="Get user subscriptions")
def get_user_subscriptions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    return services.get_all_user_subscriptions(db=db, user=current_user)


@router.get("/user-contests/pending-self-assessment", response_model=List[schemas.UserContestSubscription], summary="Get subscriptions pending self-assessment")
def get_pending_self_assessments(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    return services.get_pending_self_assessments(db=db, user=current_user)


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
    _ensure_valid_id(role_id, "role_id")
    return services.subscribe_user_to_role(db=db, user=current_user, role_id=role_id)


@router.get("/user-contests/{user_contest_id}/topic-groups", response_model=List[str])
def get_subscription_topic_groups(
    user_contest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    _ensure_valid_id(user_contest_id, "user_contest_id")
    return services.get_topic_groups_for_subscription(db=db, user=current_user, user_contest_id=user_contest_id)


@router.post("/user-contests/{user_contest_id}/proficiency",
            responses={
                409: {"description": "Self-assessment already submitted for this subscription"}
            })
def submit_proficiency_assessment(
    user_contest_id: int,
    submission: schemas.ProficiencySubmission,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    _ensure_valid_id(user_contest_id, "user_contest_id")
    # sanitize any free-text fields inside submission if present
    if hasattr(submission, "notes") and isinstance(submission.notes, str):
        submission.notes = InputValidator.sanitize_text_input(submission.notes, max_len=1000)
    return services.update_user_proficiency_by_subject(
        db=db, user=current_user, user_contest_id=user_contest_id, submission=submission
    )


@router.post("/user-contests/{user_contest_id}/generate-plan", response_model=schemas.PlanGenerationResponse)
@limit_generate_plan
def generate_study_plan_endpoint(request: Request,
    user_contest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)    
):
    _ensure_valid_id(user_contest_id, "user_contest_id")
    return services.generate_study_plan(db=db, user=current_user, user_contest_id=user_contest_id)


@router.get("/user-contests/{user_contest_id}/subjects", response_model=List[str])
def get_subscription_subjects(
    user_contest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    _ensure_valid_id(user_contest_id, "user_contest_id")
    return services.get_subjects_for_subscription(db=db, user=current_user, user_contest_id=user_contest_id)


@router.get("/user-contests/{user_contest_id}/next-session", response_model=schemas.NextStudySessionResponse)
def get_next_study_session(
    user_contest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    _ensure_valid_id(user_contest_id, "user_contest_id")
    return services.get_next_session_for_user(db=db, user=current_user, user_contest_id=user_contest_id)


@router.get("/sessions/{session_id}", response_model=schemas.StudySession)
def get_study_session_by_id(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    _ensure_valid_id(session_id, "session_id")
    return services.get_session_by_id(db=db, user=current_user, session_id=session_id)



@router.post("/user-contests/{user_contest_id}/complete-session")
def complete_session(
    user_contest_id: int,
    completion_data: schemas.SessionCompletionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    _ensure_valid_id(user_contest_id, "user_contest_id")
    # sanitize optional notes/comments fields
    if hasattr(completion_data, "notes") and isinstance(completion_data.notes, str):
        completion_data.notes = InputValidator.sanitize_text_input(completion_data.notes, max_len=1000)
    return services.complete_study_session(
        db=db, user=current_user, user_contest_id=user_contest_id, completion_data=completion_data
    )


@router.post("/generate-layout", response_model=ProceduralLayout)
def generate_layout_endpoint(
    request: schemas.LayoutGenerationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    # sanitize layout title/description if present
    if hasattr(request, "title") and isinstance(request.title, str):
        request.title = InputValidator.sanitize_text_input(request.title, max_len=200)
    if hasattr(request, "description") and isinstance(request.description, str):
        request.description = InputValidator.sanitize_text_input(request.description, max_len=1000)
    return services.generate_procedural_layout(db=db, request=request)


@router.get("/user-contests/", response_model=List[schemas.UserContestSubscription]) 
def get_all_user_subscriptions_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    return services.get_all_user_subscriptions(db=db, user=current_user)


@router.post("/sessions/{session_id}/generate-layout", response_model=ProceduralLayout)
def get_or_generate_layout_endpoint(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    _ensure_valid_id(session_id, "session_id")
    return services.get_or_generate_layout(db=db, user=current_user, session_id=session_id)
