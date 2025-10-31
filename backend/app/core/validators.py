# backend/app/core/validators.py (fix imports to match ai_schemas names)

"""
Validadores centralizados para eliminar duplicação de lógica de validação.
"""

import time
from typing import List, Set
from datetime import date

from app.core.constants import ValidationConstants
from app.core.logging import LogContext
from app.study.ai_schemas import AITopicAnalysis, AITopicAnalysisResponse, AIStudyPlanResponse


class TopicValidators:
    @staticmethod
    def validate_topic_completeness(input_ids: Set[int], output_ids: Set[int]) -> List[str]:
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
    def validate_session_estimates(analyses: List[AITopicAnalysis]) -> List[str]:
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
    def validate_priority_diversity(analyses: List[AITopicAnalysis], min_diversity: int = 2) -> List[str]:
        errors = []
        if len(analyses) <= 1:
            return errors
        priority_levels = {analysis.priority_level for analysis in analyses}
        if len(priority_levels) < min_diversity:
            errors.append(
                f"Baixa diversidade de prioridades. Encontradas: {priority_levels}. "
                f"Esperado pelo menos {min_diversity} níveis diferentes."
            )
        return errors


class StudyPlanValidators:
    @staticmethod
    def validate_session_limit(plan_response: AIStudyPlanResponse, max_sessions: int) -> List[str]:
        errors = []
        actual_sessions = len(plan_response.roadmap)
        if actual_sessions > max_sessions:
            errors.append(
                f"O plano gerado ({actual_sessions} sessões) excede o limite disponível ({max_sessions} sessões)."
            )
        return errors

    @staticmethod
    def validate_plan_completeness(plan_response: AIStudyPlanResponse, expected_topic_ids: Set[int]) -> List[str]:
        errors = []
        planned_topic_ids = set()
        for session in plan_response.roadmap:
            for topic_id in session.topic_ids:
                planned_topic_ids.add(topic_id)
        missing_ids = expected_topic_ids - planned_topic_ids
        extra_ids = planned_topic_ids - expected_topic_ids
        if missing_ids:
            errors.append(f"O plano final não incluiu os seguintes topic_ids: {missing_ids}.")
        if extra_ids:
            errors.append(f"O plano final incluiu topic_ids inventados: {extra_ids}.")
        return errors


class ContestValidators:
    @staticmethod
    def validate_exam_date(exam_date: date) -> List[str]:
        errors = []
        if not exam_date:
            errors.append("Concurso não possui data de prova definida.")
            return errors
        from datetime import date as _date
        days_until_exam = (exam_date - _date.today()).days
        if days_until_exam <= 0:
            errors.append(
                f"Data da prova ({exam_date.isoformat()}) já passou. Não é possível gerar plano de estudos."
            )
        return errors


class ValidationOrchestrator:
    @staticmethod
    def validate_analysis_phase_output(
        analysis_response: AITopicAnalysisResponse,
        input_topic_ids: Set[int],
        user_contest_id: int,
    ) -> List[str]:
        validation_start = time.time()
        all_errors = []
        with LogContext(validation_phase="analysis", user_contest_id=user_contest_id) as val_logger:
            output_ids = {analysis.topic_id for analysis in analysis_response.analyzed_topics}
            all_errors.extend(TopicValidators.validate_topic_completeness(input_topic_ids, output_ids))
            all_errors.extend(TopicValidators.validate_session_estimates(analysis_response.analyzed_topics))
            all_errors.extend(TopicValidators.validate_priority_diversity(analysis_response.analyzed_topics))
            val_logger.info(
                "Comprehensive analysis validation completed",
                duration_ms=round((time.time() - validation_start) * 1000, 2),
                total_errors=len(all_errors),
                input_topics_count=len(input_topic_ids),
                output_topics_count=len(output_ids),
            )
        return all_errors

    @staticmethod
    def validate_organization_phase_output(
        plan_response: AIStudyPlanResponse,
        input_topic_ids: Set[int],
        max_sessions: int,
        user_contest_id: int,
    ) -> List[str]:
        validation_start = time.time()
        all_errors = []
        with LogContext(validation_phase="organization", user_contest_id=user_contest_id) as val_logger:
            all_errors.extend(StudyPlanValidators.validate_session_limit(plan_response, max_sessions))
            all_errors.extend(StudyPlanValidators.validate_plan_completeness(plan_response, input_topic_ids))
            val_logger.info(
                "Comprehensive organization validation completed",
                duration_ms=round((time.time() - validation_start) * 1000, 2),
                total_errors=len(all_errors),
                planned_sessions_count=len(plan_response.roadmap),
                max_allowed_sessions=max_sessions,
            )
        return all_errors
