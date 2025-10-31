# backend/app/study/data_collector.py

"""
StudyDataCollector: Responsável por coletar dados do banco de dados.

Esta classe implementa a Single Responsibility Principle,
centralizando toda a lógica de coleta de dados para geração de planos de estudo.
"""

import time
from datetime import date
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.users.models import UserContest, UserTopicProgress
from app.contests.models import ExamStructure, ProgrammaticContent
from app.core.constants import ValidationConstants, StudyPlanConstants
from app.core.logging import get_logger, LogContext
from app.core.validators import ContestValidators


class TopicsData:
    """
    Classe de dados que encapsula todas as informações coletadas.
    """
    def __init__(self, total_sessions: int, topics_data_for_ai: List[Dict[str, Any]]):
        self.total_sessions = total_sessions
        self.topics_data_for_ai = topics_data_for_ai
        self.exam_date: date = None
        self.days_until_exam: int = 0


class StudyDataCollector:
    """
    Responsável por coletar todos os dados necessários do banco de dados
    para a geração do plano de estudos.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = get_logger("study.data_collector")
        
    def collect_topics_data(self, user_contest: UserContest) -> TopicsData:
        """
        Coleta todos os dados necessários para geração do plano de estudos.
        
        Args:
            user_contest: Contest do usuário
            
        Returns:
            TopicsData: Objeto com todos os dados coletados
            
        Raises:
            HTTPException: Se dados obrigatórios estão ausentes ou inválidos
        """
        collection_start = time.time()
        
        with LogContext(phase="data_collection", user_contest_id=user_contest.id) as phase_logger:
            phase_logger.info("Starting data collection phase")
            
            # Validar e calcular sessões disponíveis
            total_sessions = self._calculate_total_sessions(user_contest, phase_logger)
            
            # Calcular mapa de impacto das matérias
            impact_map = self._build_impact_map(user_contest, phase_logger)
            
            # Coletar tópicos com proficiência
            topics_data_for_ai = self._collect_topics_with_proficiency(
                user_contest, impact_map, phase_logger
            )
            
            collection_duration = round((time.time() - collection_start) * 1000, 2)
            
            phase_logger.info(
                "Data collection phase completed",
                duration_ms=collection_duration,
                topics_collected=len(topics_data_for_ai),
                total_sessions=total_sessions
            )
            
            topics_data = TopicsData(total_sessions, topics_data_for_ai)
            topics_data.exam_date = user_contest.role.contest.exam_date
            topics_data.days_until_exam = (topics_data.exam_date - date.today()).days
            
            return topics_data
            
    def _calculate_total_sessions(self, user_contest: UserContest, logger) -> int:
        """
        Calcula o número total de sessões disponíveis até a prova.
        
        Args:
            user_contest: Contest do usuário
            logger: Logger para logs estruturados
            
        Returns:
            int: Número total de sessões disponíveis
            
        Raises:
            HTTPException: Se a data da prova é inválida
        """
        exam_date = user_contest.role.contest.exam_date
        
        # Usar validator centralizado
        validation_errors = ContestValidators.validate_exam_date(exam_date)
        if validation_errors:
            error_message = "; ".join(validation_errors)
            logger.error("Invalid exam date", errors=validation_errors)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
            
        days_until_exam = (exam_date - date.today()).days
        total_sessions = days_until_exam * ValidationConstants.SESSIONS_PER_DAY
        
        logger.info(
            "Calculated total sessions",
            exam_date=exam_date.isoformat(),
            days_until_exam=days_until_exam,
            total_sessions=total_sessions
        )
        
        return total_sessions
        
    def _build_impact_map(self, user_contest: UserContest, logger) -> Dict[tuple, float]:
        """
        Constrói mapa de impacto efetivo das matérias baseado na estrutura da prova.
        
        Args:
            user_contest: Contest do usuário
            logger: Logger para logs estruturados
            
        Returns:
            Dict: Mapeamento de (level_type, level_name) para impacto
        """
        exam_structures = self.db.query(ExamStructure).filter(
            ExamStructure.contest_role_id == user_contest.contest_role_id
        ).all()
        
        impact_map = {}
        for structure in exam_structures:
            questions = structure.number_of_questions or 0
            weight = structure.weight_per_question or 0
            total_impact = questions * weight
            
            if total_impact > 0:
                key = (structure.level_type.value, structure.level_name)
                impact_map[key] = total_impact
                
        logger.info(
            "Built impact map from exam structures",
            exam_structures_count=len(exam_structures),
            impact_map_size=len(impact_map)
        )
        
        return impact_map
        
    def _collect_topics_with_proficiency(
        self, 
        user_contest: UserContest, 
        impact_map: Dict[tuple, float], 
        logger
    ) -> List[Dict[str, Any]]:
        """
        Coleta tópicos com suas respectivas proficiências e pesos.
        
        Args:
            user_contest: Contest do usuário
            impact_map: Mapa de impacto das matérias
            logger: Logger para logs estruturados
            
        Returns:
            List[Dict]: Lista de tópicos formatados para a IA
        """
        topics_with_proficiency = self.db.query(
            ProgrammaticContent, UserTopicProgress.current_proficiency_score
        ).join(
            UserTopicProgress, 
            UserTopicProgress.programmatic_content_id == ProgrammaticContent.id
        ).filter(
            ProgrammaticContent.contest_role_id == user_contest.contest_role_id,
            UserTopicProgress.user_contest_id == user_contest.id
        ).all()
        
        topics_data_for_ai = []
        
        for topic, proficiency in topics_with_proficiency:
            # Buscar impacto efetivo: primeiro por SUBJECT, depois por MODULE
            effective_impact = impact_map.get(("SUBJECT", topic.subject))
            if effective_impact is None:
                effective_impact = impact_map.get(
                    ("MODULE", topic.exam_module), 
                    StudyPlanConstants.DEFAULT_IMPACT_WEIGHT
                )
            
            topics_data_for_ai.append({
                "topic_id": topic.id,
                "exam_module": topic.exam_module,
                "subject": topic.subject,
                "topic_name": topic.topic,
                "proficiency": proficiency,
                "subject_weight": effective_impact
            })
            
        logger.info(
            "Collected topics with proficiency",
            topics_count=len(topics_data_for_ai)
        )
        
        return topics_data_for_ai
