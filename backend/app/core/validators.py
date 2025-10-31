# backend/app/core/validators.py

"""
Validadores centralizados para eliminar duplicação de lógica de validação.

Este módulo centraliza todas as validações determinísticas que são
reutilizadas em diferentes partes do sistema.
"""

import time
from typing import List, Set, Dict, Any
from datetime import date

from app.core.constants import ValidationConstants
from app.core.logging import get_logger, LogContext
from app.study.ai_schemas import AnalyzedTopicData, AITopicAnalysisResponse, AIStudyPlanResponse


class TopicValidators:
    """Validadores centralizados para tópicos de estudo"""
    
    @staticmethod
    def validate_topic_completeness(input_ids: Set[int], output_ids: Set[int]) -> List[str]:
        """
        Valida se todos os tópicos de entrada estão na saída.
        
        Args:
            input_ids: Conjunto de IDs de tópicos de entrada
            output_ids: Conjunto de IDs de tópicos de saída
            
        Returns:
            Lista de erros encontrados (vazia se validação passou)
        """
        errors = []
        if input_ids != output_ids:
            missing = input_ids - output_ids
            extra = output_ids - input_ids
            if missing:
                errors.append(f"Tópicos ausentes: {missing}")
            if extra:
                errors.append(f"Tópicos inventados: {extra}")
        return errors
    
    @staticmethod
    def validate_session_estimates(analyses: List[AnalyzedTopicData]) -> List[str]:
        """
        Valida estimativas de sessões de estudo.
        
        Args:
            analyses: Lista de tópicos analisados com estimativas
            
        Returns:
            Lista de erros encontrados (vazia se validação passou)
        """
        errors = []
        for analysis in analyses:
            sessions = analysis.estimated_sessions
            if not (1 <= sessions <= ValidationConstants.MAX_SESSIONS_ESTIMATE):
                errors.append(
                    f"Sessões inválidas ({sessions}) para tópico {analysis.topic_id}. "
                    f"Deve estar entre 1 e {ValidationConstants.MAX_SESSIONS_ESTIMATE}."
                )
        return errors
    
    @staticmethod 
    def validate_priority_diversity(analyses: List[AnalyzedTopicData], min_diversity: int = 2) -> List[str]:
        """
        Valida se há diversidade suficiente nos níveis de prioridade.
        
        Args:
            analyses: Lista de tópicos analisados
            min_diversity: Mínimo de níveis de prioridade diferentes esperados
            
        Returns:
            Lista de erros encontrados (vazia se validação passou)
        """
        errors = []
        if len(analyses) <= 1:
            return errors  # Com 1 tópico ou menos, não faz sentido validar diversidade
            
        priority_levels = {analysis.priority_level for analysis in analyses}
        if len(priority_levels) < min_diversity:
            errors.append(
                f"Baixa diversidade de prioridades. Encontradas: {priority_levels}. "
                f"Esperado pelo menos {min_diversity} níveis diferentes."
            )
        return errors


class StudyPlanValidators:
    """Validadores centralizados para planos de estudo"""
    
    @staticmethod
    def validate_session_limit(plan_response: AIStudyPlanResponse, max_sessions: int) -> List[str]:
        """
        Valida se o plano gerado não excede o limite de sessões disponíveis.
        
        Args:
            plan_response: Resposta da IA com o plano organizado
            max_sessions: Número máximo de sessões permitidas
            
        Returns:
            Lista de erros encontrados (vazia se validação passou)
        """
        errors = []
        actual_sessions = len(plan_response.roadmap)
        if actual_sessions > max_sessions:
            errors.append(
                f"O plano gerado ({actual_sessions} sessões) excede o limite "
                f"disponível ({max_sessions} sessões)."
            )
        return errors
    
    @staticmethod
    def validate_plan_completeness(plan_response: AIStudyPlanResponse, expected_topic_ids: Set[int]) -> List[str]:
        """
        Valida se todos os tópicos esperados estão incluídos no plano final.
        
        Args:
            plan_response: Resposta da IA com o plano organizado
            expected_topic_ids: Conjunto de IDs de tópicos esperados
            
        Returns:
            Lista de erros encontrados (vazia se validação passou)
        """
        errors = []
        planned_topic_ids = set()
        
        for session in plan_response.roadmap:
            for topic_id in session.topic_ids:
                planned_topic_ids.add(topic_id)
        
        missing_ids = expected_topic_ids - planned_topic_ids
        extra_ids = planned_topic_ids - expected_topic_ids
        
        if missing_ids:
            errors.append(
                f"O plano final não incluiu os seguintes topic_ids: {missing_ids}."
            )
        if extra_ids:
            errors.append(
                f"O plano final incluiu topic_ids inventados: {extra_ids}."
            )
            
        return errors


class ContestValidators:
    """Validadores centralizados para processamento de concursos/editais"""
    
    @staticmethod
    def validate_topic_consistency(initial_topics: Set[str], refined_topics: Set[str]) -> List[str]:
        """
        Valida consistência entre tópicos extraídos e refinados na IA.
        
        Args:
            initial_topics: Conjunto de tópicos da extração inicial
            refined_topics: Conjunto de tópicos após refinamento
            
        Returns:
            Lista de erros encontrados (vazia se validação passou)
        """
        errors = []
        
        if initial_topics != refined_topics:
            missing_from_refined = initial_topics - refined_topics
            added_in_refined = refined_topics - initial_topics
            
            if missing_from_refined:
                errors.append(f"IA de refinamento removeu tópicos: {missing_from_refined}")
            if added_in_refined:
                errors.append(f"IA de refinamento inventou tópicos: {added_in_refined}")
        
        return errors
    
    @staticmethod
    def validate_exam_date(exam_date: date) -> List[str]:
        """
        Valida se a data da prova é válida para geração de plano de estudos.
        
        Args:
            exam_date: Data da prova
            
        Returns:
            Lista de erros encontrados (vazia se validação passou)
        """
        errors = []
        
        if not exam_date:
            errors.append("Concurso não possui data de prova definida.")
            return errors
            
        days_until_exam = (exam_date - date.today()).days
        if days_until_exam <= 0:
            errors.append(
                f"Data da prova ({exam_date.isoformat()}) já passou. "
                f"Não é possível gerar plano de estudos."
            )
            
        return errors


class ValidationOrchestrator:
    """
    Orquestrador que combina diferentes validadores para fluxos complexos.
    """
    
    @staticmethod
    def validate_analysis_phase_output(
        analysis_response: AITopicAnalysisResponse,
        input_topic_ids: Set[int],
        user_contest_id: int
    ) -> List[str]:
        """
        Executa todas as validações necessárias para a fase de análise de tópicos.
        
        Args:
            analysis_response: Resposta da IA com análise de tópicos
            input_topic_ids: IDs dos tópicos de entrada
            user_contest_id: ID do contest do usuário (para logs)
            
        Returns:
            Lista de todos os erros encontrados
        """
        validation_start = time.time()
        all_errors = []
        
        with LogContext(validation_phase="analysis", user_contest_id=user_contest_id) as val_logger:
            val_logger.debug("Starting comprehensive analysis validation")
            
            # Validação 1: Completude dos tópicos
            output_ids = {analysis.topic_id for analysis in analysis_response.analyzed_topics}
            completeness_errors = TopicValidators.validate_topic_completeness(input_topic_ids, output_ids)
            all_errors.extend(completeness_errors)
            
            # Validação 2: Estimativas de sessões
            session_errors = TopicValidators.validate_session_estimates(analysis_response.analyzed_topics)
            all_errors.extend(session_errors)
            
            # Validação 3: Diversidade de prioridades
            diversity_errors = TopicValidators.validate_priority_diversity(analysis_response.analyzed_topics)
            all_errors.extend(diversity_errors)
            
            validation_duration = round((time.time() - validation_start) * 1000, 2)
            
            val_logger.info(
                "Comprehensive analysis validation completed",
                duration_ms=validation_duration,
                total_errors=len(all_errors),
                input_topics_count=len(input_topic_ids),
                output_topics_count=len(output_ids)
            )
            
        return all_errors
    
    @staticmethod
    def validate_organization_phase_output(
        plan_response: AIStudyPlanResponse,
        input_topic_ids: Set[int],
        max_sessions: int,
        user_contest_id: int
    ) -> List[str]:
        """
        Executa todas as validações necessárias para a fase de organização do plano.
        
        Args:
            plan_response: Resposta da IA com plano organizado
            input_topic_ids: IDs dos tópicos de entrada
            max_sessions: Número máximo de sessões permitidas
            user_contest_id: ID do contest do usuário (para logs)
            
        Returns:
            Lista de todos os erros encontrados
        """
        validation_start = time.time()
        all_errors = []
        
        with LogContext(validation_phase="organization", user_contest_id=user_contest_id) as val_logger:
            val_logger.debug("Starting comprehensive organization validation")
            
            # Validação 1: Limite de sessões
            limit_errors = StudyPlanValidators.validate_session_limit(plan_response, max_sessions)
            all_errors.extend(limit_errors)
            
            # Validação 2: Completude dos tópicos no plano
            completeness_errors = StudyPlanValidators.validate_plan_completeness(plan_response, input_topic_ids)
            all_errors.extend(completeness_errors)
            
            validation_duration = round((time.time() - validation_start) * 1000, 2)
            
            val_logger.info(
                "Comprehensive organization validation completed",
                duration_ms=validation_duration,
                total_errors=len(all_errors),
                planned_sessions_count=len(plan_response.roadmap),
                max_allowed_sessions=max_sessions
            )
            
        return all_errors
