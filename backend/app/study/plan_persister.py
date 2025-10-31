# backend/app/study/plan_persister.py

"""
StudyPlanPersister: Responsável pela persistência no banco de dados.

Esta classe implementa a Single Responsibility Principle,
centralizando toda a lógica de persistência de planos de estudo.
"""

import time
from typing import Dict
from sqlalchemy.orm import Session

from app.users.models import UserContest
from app.contests.models import ProgrammaticContent
from app.core.logging import get_logger, LogContext
from app.study.ai_schemas import AIStudyPlanResponse
from app.study.models import StudyRoadmapSession


class StudyPlanPersister:
    """
    Responsável pela persistência do plano final no banco de dados.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger("study.plan_persister")
        
    def save_plan(
        self, 
        user_contest: UserContest, 
        plan: AIStudyPlanResponse
    ) -> int:
        """
        Persiste o plano final no banco de dados.
        
        Args:
            user_contest: Contest do usuário
            plan: Plano organizado pela IA
            
        Returns:
            int: Número de sessões criadas
            
        Raises:
            Exception: Se houver erro na persistência
        """
        persistence_start = time.time()
        
        with LogContext(phase="database_persistence", user_contest_id=user_contest.id) as phase_logger:
            phase_logger.info(
                "Starting database persistence phase",
                roadmap_sessions_to_save=len(plan.roadmap)
            )
            
            try:
                # Limpar roadmap anterior
                deleted_count = self._clear_previous_roadmap(user_contest, phase_logger)
                
                # Preparar mapeamento de tópicos
                topic_id_to_obj_map = self._build_topic_mapping(user_contest, phase_logger)
                
                # Criar novas sessões
                sessions_created = self._create_new_sessions(
                    user_contest, plan, topic_id_to_obj_map, phase_logger
                )
                
                # Commit das mudanças
                self.db.commit()
                
                persistence_duration = round((time.time() - persistence_start) * 1000, 2)
                
                phase_logger.info(
                    "Database persistence phase completed",
                    duration_ms=persistence_duration,
                    sessions_created=sessions_created,
                    sessions_deleted=deleted_count
                )
                
                return sessions_created
                
            except Exception as e:
                # Rollback em caso de erro
                self.db.rollback()
                phase_logger.error(
                    "Database persistence failed - rolling back",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
                
    def _clear_previous_roadmap(self, user_contest: UserContest, logger) -> int:
        """
        Remove o roadmap anterior do usuário.
        
        Args:
            user_contest: Contest do usuário
            logger: Logger para registrar ação
            
        Returns:
            int: Número de sessões removidas
        """
        deleted_count = self.db.query(StudyRoadmapSession).filter(
            StudyRoadmapSession.user_contest_id == user_contest.id
        ).delete()
        
        logger.info(
            "Cleared previous roadmap sessions",
            deleted_sessions_count=deleted_count
        )
        
        return deleted_count
        
    def _build_topic_mapping(self, user_contest: UserContest, logger) -> Dict[int, ProgrammaticContent]:
        """
        Constrói mapeamento de IDs de tópicos para objetos do banco.
        
        Args:
            user_contest: Contest do usuário
            logger: Logger para registrar ação
            
        Returns:
            Dict: Mapeamento id -> objeto ProgrammaticContent
        """
        all_user_topics = self.db.query(ProgrammaticContent).filter(
            ProgrammaticContent.contest_role_id == user_contest.contest_role_id
        ).all()
        
        topic_id_to_obj_map = {topic.id: topic for topic in all_user_topics}
        
        logger.info(
            "Built topic ID mapping",
            total_topics_available=len(topic_id_to_obj_map)
        )
        
        return topic_id_to_obj_map
        
    def _create_new_sessions(
        self,
        user_contest: UserContest,
        plan: AIStudyPlanResponse,
        topic_id_to_obj_map: Dict[int, ProgrammaticContent],
        logger
    ) -> int:
        """
        Cria novas sessões de estudo baseadas no plano da IA.
        
        Args:
            user_contest: Contest do usuário
            plan: Plano organizado pela IA
            topic_id_to_obj_map: Mapeamento de IDs para objetos de tópicos
            logger: Logger para registrar ação
            
        Returns:
            int: Número de sessões criadas
        """
        new_sessions_to_add = []
        skipped_sessions = 0
        
        for session_data in plan.roadmap:
            topic_ids_list = session_data.topic_ids or []
            
            if not topic_ids_list:
                skipped_sessions += 1
                logger.warning(
                    "Skipping session with no topics",
                    session_number=session_data.session_number
                )
                continue
                
            # Criar nova sessão
            new_session = StudyRoadmapSession(
                user_contest_id=user_contest.id,
                session_number=session_data.session_number,
                summary=session_data.summary,
                priority_level=session_data.priority_level,
                priority_reason=session_data.priority_reason
            )
            
            # Associar tópicos existentes
            topics_in_session = [
                topic_id_to_obj_map.get(tid) 
                for tid in topic_ids_list 
                if tid in topic_id_to_obj_map
            ]
            
            if topics_in_session:
                new_session.topics = topics_in_session
                new_sessions_to_add.append(new_session)
            else:
                skipped_sessions += 1
                logger.warning(
                    "Skipping session with no valid topics",
                    session_number=session_data.session_number,
                    invalid_topic_ids=topic_ids_list
                )
                
        # Adicionar todas as sessões ao banco
        self.db.add_all(new_sessions_to_add)
        
        logger.info(
            "Created new roadmap sessions",
            sessions_created=len(new_sessions_to_add),
            sessions_skipped=skipped_sessions
        )
        
        return len(new_sessions_to_add)
