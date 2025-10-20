# Em backend/app/study/services.py
import json
from datetime import date
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from app.core import ai_service
from app.users.models import User, UserContest, UserTopicProgress
from app.contests.models import ContestRole, ProgrammaticContent, ExamStructure
from .schemas import ProficiencySubmission
from app.users.models import AssessmentType, ProficiencyHistory
from .models import StudyRoadmapSession
from .ai_schemas import AITopicAnalysisResponse, AIStudyPlanResponse
from .prompts import topic_analysis_prompt, plan_organization_prompt
from .plan_generator import StudyPlanGenerator

def subscribe_user_to_role(db: Session, user: User, role_id: int):
    # Verifica se o cargo existe
    role = db.query(ContestRole).filter(ContestRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Verifica se o usuário já está inscrito
    existing_subscription = db.query(UserContest).filter(
        UserContest.user_id == user.id,
        UserContest.contest_role_id == role_id
    ).first()
    if existing_subscription:
        return existing_subscription # Retorna a inscrição existente

    # Cria a nova inscrição (UserContest)
    new_user_contest = UserContest(user_id=user.id, contest_role_id=role_id)
    db.add(new_user_contest)
    db.flush() # Para obter o ID do new_user_contest

    # Popula o progresso do usuário para cada tópico do cargo, com proficiência inicial 0
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

def get_topic_groups_for_subscription(db: Session, user: User, user_contest_id: int):
    user_contest = db.query(UserContest).filter(UserContest.id == user_contest_id).first()
    # Validação de segurança: o usuário só pode ver seus próprios grupos
    if not user_contest or user_contest.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    # Query para buscar os nomes distintos dos grupos de tópicos
    topic_groups = db.query(ProgrammaticContent.topic).filter(
        ProgrammaticContent.contest_role_id == user_contest.contest_role_id
    ).distinct().all()

    # Converte o resultado (uma lista de tuplas) para uma lista de strings
    return [group[0] for group in topic_groups]

def update_user_proficiency_by_subject(db: Session, user: User, user_contest_id: int, submission: ProficiencySubmission):
    user_contest = db.query(UserContest).filter(UserContest.id == user_contest_id, UserContest.user_id == user.id).first()
    if not user_contest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    # Itera sobre cada matéria e nota enviada pelo usuário
    for proficiency_update in submission.proficiencies:
        subject_name = proficiency_update.subject
        new_score = proficiency_update.score

        # Encontra todos os registros de UserTopicProgress cuja matéria (subject) corresponde
        progress_records_to_update = db.query(UserTopicProgress).join(UserTopicProgress.topic).filter(
            UserTopicProgress.user_contest_id == user_contest_id,
            ProgrammaticContent.subject == subject_name
        ).all()

        # Para cada tópico dentro da matéria, atualiza o score e cria um registro de histórico
        for progress in progress_records_to_update:
            progress.current_proficiency_score = new_score
            
            history_record = ProficiencyHistory(
                topic_progress=progress,
                score=new_score,
                assessment_type=AssessmentType.SELF_ASSESSMENT
            )
            db.add(history_record)
    
    db.commit()
    return {"status": "success", "message": "Proficiency updated and history recorded."}

def generate_study_plan(db: Session, user: User, user_contest_id: int):
    user_contest = db.query(UserContest).filter(
        UserContest.id == user_contest_id, UserContest.user_id == user.id
    ).first()

    if not user_contest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    # Instancia e executa o gerador
    generator = StudyPlanGenerator(db=db, user_contest=user_contest)
    result = generator.generate()
    
    return result

def get_subjects_for_subscription(db: Session, user: User, user_contest_id: int):
    user_contest = db.query(UserContest).filter(UserContest.id == user_contest_id, UserContest.user_id == user.id).first()
    if not user_contest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    # Query para buscar os nomes distintos dos subjects
    subjects = db.query(ProgrammaticContent.subject).filter(
        ProgrammaticContent.contest_role_id == user_contest.contest_role_id
    ).distinct().all()

    # Converte a lista de tuplas para uma lista de strings
    return [subject[0] for subject in subjects]