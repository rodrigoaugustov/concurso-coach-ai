# Em backend/app/study/services.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.users.models import User, UserContest, UserTopicProgress
from app.contests.models import ContestRole, ProgrammaticContent
from .schemas import ProficiencySubmission
from app.users.models import AssessmentType, ProficiencyHistory

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
    topic_groups = db.query(ProgrammaticContent.topic_group).filter(
        ProgrammaticContent.contest_role_id == user_contest.contest_role_id
    ).distinct().all()

    # Converte o resultado (uma lista de tuplas) para uma lista de strings
    return [group[0] for group in topic_groups]

def update_user_proficiency_by_group(db: Session, user: User, user_contest_id: int, submission: ProficiencySubmission):
    user_contest = db.query(UserContest).filter(UserContest.id == user_contest_id, UserContest.user_id == user.id).first()
    if not user_contest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    # Itera sobre cada grupo e nota enviados pelo usuário
    for proficiency_update in submission.proficiencies:
        group_name = proficiency_update.topic_group
        new_score = proficiency_update.score

        # Encontra todos os registros de UserTopicProgress para este usuário e grupo de tópicos
        progress_records = db.query(UserTopicProgress).join(UserTopicProgress.topic).filter(
            UserTopicProgress.user_contest_id == user_contest_id,
            ProgrammaticContent.topic_group == group_name
        ).all()

        # Para cada tópico dentro do grupo, atualiza o score e cria um registro de histórico
        for progress in progress_records:
            # Na auto-avaliação, o novo score simplesmente substitui o antigo.
            # (A lógica ponderada será usada para quizzes no futuro)
            progress.current_proficiency_score = new_score
            
            # Cria o registro no histórico
            history_record = ProficiencyHistory(
                topic_progress=progress,
                score=new_score,
                assessment_type=AssessmentType.SELF_ASSESSMENT
            )
            db.add(history_record)
    
    db.commit()
    return {"status": "success", "message": "Proficiency updated and history recorded."}
