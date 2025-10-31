# backend/app/study/plan_organizer.py

"""
StudyPlanOrganizer: Responsável pela organização final do plano de estudos.

Esta classe implementa a Single Responsibility Principle,
centralizando toda a lógica de organização de planos de estudo via IA.
"""

import json
import time
from typing import List, Set

from app.core.ai_service import LangChainService
from app.core.constants import AIConstants
from app.core.logging import get_logger, LogContext
from app.core.validators import ValidationOrchestrator
from app.study.ai_schemas import AITopicAnalysisResponse, AIStudyPlanResponse
from app.study.prompts import plan_organization_prompt


class StudyPlanOrganizer:
    """
    Responsável pela organização final do plano de estudos,
    incluindo validação e auto-correção.
    """
    
    def __init__(self, ai_service: LangChainService):
        self.ai_service = ai_service
        self.logger = get_logger("study.plan_organizer")
        
    def organize_plan(
        self,
        analysis: AITopicAnalysisResponse,
        total_sessions: int,
        input_topic_ids: Set[int],
        user_contest_id: int
    ) -> AIStudyPlanResponse:
        """
        Organiza o plano final de estudos usando IA com validação e auto-correção.
        
        Args:
            analysis: Análise de tópicos da IA
            total_sessions: Número total de sessões disponíveis
            input_topic_ids: IDs dos tópicos de entrada (para validação)
            user_contest_id: ID do contest do usuário (para logs)
            
        Returns:
            AIStudyPlanResponse: Plano organizado pela IA
            
        Raises:
            Exception: Se a IA falhar após todas as tentativas
        """
        organization_start = time.time()
        
        with LogContext(phase="plan_organization", user_contest_id=user_contest_id) as phase_logger:
            phase_logger.info(
                "Starting plan organization phase",
                total_sessions=total_sessions,
                analyzed_topics_count=len(analysis.analyzed_topics)
            )
            
            # Preparar entrada para a IA
            analyzed_data = analysis.dict()
            prompt_input = {
                "total_sessions": total_sessions,
                "analyzed_topics_json": json.dumps(analyzed_data, indent=2)
            }
            
            # Executar organização com validação e auto-correção
            final_plan_obj = self._invoke_ai_with_validation(
                prompt_input=prompt_input,
                total_sessions=total_sessions,
                input_topic_ids=input_topic_ids,
                user_contest_id=user_contest_id
            )
            
            organization_duration = round((time.time() - organization_start) * 1000, 2)
            
            # Log estatísticas do plano
            priority_session_counts = self._count_session_priorities(final_plan_obj)
            
            phase_logger.info(
                "Plan organization phase completed",
                duration_ms=organization_duration,
                roadmap_sessions_count=len(final_plan_obj.roadmap),
                priority_session_distribution=priority_session_counts
            )
            
            return final_plan_obj
            
    def _invoke_ai_with_validation(
        self,
        prompt_input: dict,
        total_sessions: int,
        input_topic_ids: Set[int],
        user_contest_id: int
    ) -> AIStudyPlanResponse:
        """
        Invoca a IA com ciclo de validação e auto-correção.
        
        Args:
            prompt_input: Dados de entrada para o prompt
            total_sessions: Número máximo de sessões
            input_topic_ids: IDs dos tópicos de entrada (para validação)
            user_contest_id: ID do contest do usuário
            
        Returns:
            AIStudyPlanResponse: Resposta validada da IA
        """
        from app.study.ai_validation_service import AIValidationService
        
        validation_service = AIValidationService(
            ai_service=self.ai_service,
            max_retries=AIConstants.MAX_RETRIES_AI_VALIDATION
        )
        
        # Função de validação específica para organização de plano
        def validate_plan_response(response: AIStudyPlanResponse) -> List[str]:
            return ValidationOrchestrator.validate_organization_phase_output(
                plan_response=response,
                input_topic_ids=input_topic_ids,
                max_sessions=total_sessions,
                user_contest_id=user_contest_id
            )
        
        return validation_service.invoke_with_validation(
            prompt_template=plan_organization_prompt,
            prompt_input=prompt_input,
            response_schema=AIStudyPlanResponse,
            validation_function=validate_plan_response,
            context={"phase": "plan_organization", "user_contest_id": user_contest_id}
        )
        
    def _count_session_priorities(self, plan_response: AIStudyPlanResponse) -> dict:
        """
        Conta a distribuição de prioridades nas sessões para logs.
        
        Args:
            plan_response: Resposta do plano organizado
            
        Returns:
            dict: Contagem de sessões por prioridade
        """
        priority_session_counts = {}
        for session in plan_response.roadmap:
            priority = session.priority_level
            priority_session_counts[priority] = priority_session_counts.get(priority, 0) + 1
        return priority_session_counts
