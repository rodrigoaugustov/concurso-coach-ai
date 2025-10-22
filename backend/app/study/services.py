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
# Define os intervalos em dias para a revisão.
# Ex: 1 dia, 3 dias depois, 7 dias depois, 14 dias depois, etc.
SPACED_REPETITION_INTERVALS = [1, 3, 7, 14, 30, 60]


def subscribe_user_to_role(db: Session, user: User, role_id: int):
    # Verifica se o cargo existe
    role = db.query(ContestRole).filter(ContestRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # VALIDAÇÃO: Verifica se o usuário já está inscrito neste cargo
    existing_subscription = db.query(UserContest).filter(
        UserContest.user_id == user.id,
        UserContest.contest_role_id == role_id
    ).first()
    
    if existing_subscription:
        # Retorna erro 409 Conflict se já estiver inscrito
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=f"Usuário já está inscrito no cargo '{role.job_title}' deste concurso."
        )

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

def get_available_roles_for_user(db: Session, user: User):
    """
    Retorna uma lista de cargos disponíveis para inscrição, 
    filtrando aqueles em que o usuário já está inscrito.
    """
    # Subconsulta para obter os role_ids em que o usuário já está inscrito
    enrolled_role_ids = db.query(UserContest.contest_role_id).filter(
        UserContest.user_id == user.id
    ).subquery()
    
    # Query principal: busca cargos de concursos COMPLETED que o usuário NÃO está inscrito
    available_roles = db.query(ContestRole).join(
        PublishedContest, ContestRole.published_contest_id == PublishedContest.id
    ).filter(
        PublishedContest.status == ContestStatus.COMPLETED,
        ~ContestRole.id.in_(enrolled_role_ids)  # Exclui cargos já inscritos
    ).order_by(
        PublishedContest.name, ContestRole.job_title
    ).all()
    
    return available_roles

def get_user_enrolled_roles(db: Session, user: User):
    """
    Retorna uma lista de cargos em que o usuário está inscrito.
    """
    enrolled_subscriptions = db.query(UserContest).options(
        joinedload(UserContest.role).joinedload(ContestRole.contest)
    ).filter(
        UserContest.user_id == user.id
    ).order_by(
        UserContest.id.desc()
    ).all()
    
    return enrolled_subscriptions

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

def get_next_session_for_user(db: Session, user: User, user_contest_id: int):
    # 1. VALIDAÇÃO (como antes)
    user_contest = db.query(UserContest).filter(
        UserContest.id == user_contest_id, UserContest.user_id == user.id
    ).first()
    if not user_contest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found for this user.")

    # ===================================================================
    # 2. BUSCA A SESSÃO DE REVISÃO (Usando a lógica validada pelo debug)
    # ===================================================================
    review_session_obj = None
    
    # Query 1: Encontra o PRIMEIRO tópico de progresso que está atrasado.
    overdue_progress = db.query(UserTopicProgress).filter(
        UserTopicProgress.user_contest_id == user_contest_id,
        UserTopicProgress.next_review_at != None,
        UserTopicProgress.next_review_at <= datetime.utcnow()
    ).order_by(
        UserTopicProgress.next_review_at.asc()
    ).first()

    if overdue_progress:
        # Query 2: Se encontrou um tópico, busca a sessão que o contém.
        # Usamos options(joinedload(...)) para garantir que os tópicos da sessão sejam carregados.
        review_session_obj = db.query(StudyRoadmapSession).options(
            joinedload(StudyRoadmapSession.topics)
        ).join(
            roadmap_session_topics
        ).filter(
            StudyRoadmapSession.user_contest_id == user_contest_id,
            roadmap_session_topics.c.topic_id == overdue_progress.programmatic_content_id
        ).first()

    # ===================================================================
    # 3. BUSCA A PRÓXIMA SESSÃO PRINCIPAL (Usando a lógica que já funciona)
    # ===================================================================
    last_completed_session_number = db.query(
        func.max(StudyRoadmapSession.session_number)
    ).join(
        roadmap_session_topics, StudyRoadmapSession.id == roadmap_session_topics.c.session_id
    ).join(
        UserTopicProgress, UserTopicProgress.programmatic_content_id == roadmap_session_topics.c.topic_id
    ).filter(
        UserTopicProgress.user_contest_id == user_contest_id,
        UserTopicProgress.sessions_studied > 0
    ).scalar()

    next_session_number = None
    if last_completed_session_number is not None:
        next_session_number = last_completed_session_number + 1
    else:
        first_session_number = db.query(func.min(StudyRoadmapSession.session_number)).filter(
            StudyRoadmapSession.user_contest_id == user_contest_id
        ).scalar()
        next_session_number = first_session_number

    next_main_session = None
    if next_session_number is not None:
        next_main_session = db.query(StudyRoadmapSession).options(
            joinedload(StudyRoadmapSession.topics)
        ).filter(
            StudyRoadmapSession.user_contest_id == user_contest_id,
            StudyRoadmapSession.session_number == next_session_number
        ).first()

    if not next_main_session:
        plan_exists = db.query(StudyRoadmapSession).filter(StudyRoadmapSession.user_contest_id == user_contest_id).first()
        if not plan_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano de estudos não encontrado. Por favor, gere o plano primeiro.")
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parabéns! Você concluiu seu plano de estudos.")

    # ===================================================================
    # 4. RETORNA A RESPOSTA FINAL
    # ===================================================================
    return {
        "main_session": next_main_session,
        "review_session": review_session_obj
    }

def complete_study_session(db: Session, user: User, user_contest_id: int, completion_data: SessionCompletionRequest):
    user_contest = db.query(UserContest).filter(
        UserContest.id == user_contest_id, UserContest.user_id == user.id
    ).first()
    if not user_contest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    now = datetime.utcnow()

    # --- ATUALIZA A SESSÃO PRINCIPAL ---
    main_session = db.query(StudyRoadmapSession).options(joinedload(StudyRoadmapSession.topics)).filter(
        StudyRoadmapSession.id == completion_data.main_session_id,
        StudyRoadmapSession.user_contest_id == user_contest_id
    ).first()

    if not main_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main session not found in roadmap.")

    # Atualiza o progresso para todos os tópicos da sessão principal
    for topic in main_session.topics:
        progress = db.query(UserTopicProgress).filter(
            UserTopicProgress.user_contest_id == user_contest_id,
            UserTopicProgress.programmatic_content_id == topic.id
        ).first()
        
        if progress:
            progress.sessions_studied += 1
            progress.last_studied_at = now
            # Agenda a primeira revisão para 1 dia a partir de agora
            progress.next_review_at = now + timedelta(days=SPACED_REPETITION_INTERVALS[0])

    # --- ATUALIZA A SESSÃO DE REVISÃO (se houver) ---
    if completion_data.review_session_id:
        review_session = db.query(StudyRoadmapSession).options(joinedload(StudyRoadmapSession.topics)).filter(
            StudyRoadmapSession.id == completion_data.review_session_id,
            StudyRoadmapSession.user_contest_id == user_contest_id
        ).first()

        if review_session:
            # Itera sobre TODOS os tópicos da sessão de revisão
            for topic in review_session.topics:
                review_progress = db.query(UserTopicProgress).filter(
                    UserTopicProgress.user_contest_id == user_contest_id,
                    UserTopicProgress.programmatic_content_id == topic.id
                ).first()

                if review_progress:
                    # A lógica de cálculo do próximo intervalo permanece a mesma
                    current_interval_index = (review_progress.sessions_studied - 1) % len(SPACED_REPETITION_INTERVALS)
                    next_interval_index = min(current_interval_index + 1, len(SPACED_REPETITION_INTERVALS) - 1)
                    days_for_next_review = SPACED_REPETITION_INTERVALS[next_interval_index]
                    
                    review_progress.next_review_at = now + timedelta(days=days_for_next_review)
                    review_progress.sessions_studied += 1 # Incrementa para avançar no ciclo de revisão

    db.commit()
    return {"status": "success", "message": "Session completed and progress updated."}

def generate_procedural_layout(db: Session, request: LayoutGenerationRequest):
    topics = db.query(ProgrammaticContent).filter(
        ProgrammaticContent.id.in_(request.topic_ids)
    ).all()
    if not topics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topics not found.")

    topic_names = [t.topic for t in topics]
    topics_list_str = "\n- ".join(topic_names)

    prompt_input = {"topics_list_str": topics_list_str}

    ai_service = LangChainService(
        provider="google",
        api_key=settings.GEMINI_API_KEY,
        model_name="gemini-2.5-pro"
    )
    
    # Chama a IA esperando o schema do layout procedural
    ai_response_obj = ai_service.generate_structured_output(
        prompt_template=procedural_layout_prompt,
        prompt_input=prompt_input,
        response_schema=ProceduralLayout
    )
    
    return ai_response_obj

def get_all_user_subscriptions(db: Session, user: User):
    """Retorna TODAS as inscrições de concurso para o usuário logado."""
    return db.query(UserContest).options(
        joinedload(UserContest.role).joinedload(ContestRole.contest)
    ).filter(
        UserContest.user_id == user.id
    ).order_by(
        UserContest.id.desc()
    ).all()

def get_or_generate_layout(db: Session, user: User, session_id: int):
    """
    Obtém o layout da aula para uma sessão.
    Se o layout ainda não foi gerado, ele aciona a IA para criá-lo,
    salva o resultado, e o retorna. Se já existe, retorna do cache do banco.
    """
    # 1. Busca a sessão e valida a posse do usuário de forma segura
    session = db.query(StudyRoadmapSession).options(
        joinedload(StudyRoadmapSession.topics) # Carrega os tópicos junto
    ).join(
        UserContest, StudyRoadmapSession.user_contest_id == UserContest.id
    ).filter(
        StudyRoadmapSession.id == session_id,
        UserContest.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessão de estudo não encontrada ou não pertence ao usuário.")

    # 2. VERIFICA SE O CONTEÚDO JÁ EXISTE NO BANCO (CACHE)
    if session.generated_content:
        # Valida o JSON do banco com o schema Pydantic antes de retornar
        validated_layout = ProceduralLayout.model_validate(session.generated_content)
        return validated_layout

    # 3. SE NÃO EXISTE, GERA, SALVA E RETORNA
    
    # Prepara os dados para o prompt
    topic_names = [t.topic for t in session.topics]
    topics_list_str = "\n- ".join(topic_names)
    prompt_input = {"topics_list_str": topics_list_str}

    # Instancia o serviço de IA
    ai_service = LangChainService(
        provider="google",
        api_key=settings.GEMINI_API_KEY,
        model_name="gemini-2.5-pro"
    )
    
    # Chama a IA para gerar o layout
    ai_response_obj = ai_service.generate_structured_output(
        prompt_template=procedural_layout_prompt,
        prompt_input=prompt_input,
        response_schema=ProceduralLayout
    )
    
    # Salva o resultado (como dicionário) na coluna JSONB
    session.generated_content = ai_response_obj.model_dump()
    db.commit()
    
    return ai_response_obj
