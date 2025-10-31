# backend/app/study/topic_analyzer.py

"""
StudyTopicAnalyzer: Responsável pela análise de tópicos via IA.

Esta classe implementa a Single Responsibility Principle,
centralizando toda a lógica de análise de tópicos com IA.
"""

import json
import time
from typing import List

from app.core.ai_service import LangChainService
from app.core.constants import AIConstants
from app.core.logging import get_logger, LogContext
from app.core.validators import ValidationOrchestrator
from app.study.ai_schemas import AITopicAnalysisResponse
from app.study.data_collector import TopicsData
from app.study.prompts import topic_analysis_prompt


class StudyTopicAnalyzer:
    """
    Responsável pela análise de tópicos via IA,
    incluindo validação e auto-correção.
    """
    
    def __init__(self, ai_service: LangChainService):
        self.ai_service = ai_service
        self.logger = get_logger("study.topic_analyzer")
        
    def analyze_topics(
        self, 
        topics_data: TopicsData, 
        user_contest_id: int
    ) -> AITopicAnalysisResponse:
        """
        Analisa tópicos usando IA com validação e auto-correção.
        
        Args:
            topics_data: Dados dos tópicos coletados
            user_contest_id: ID do contest do usuário (para logs)
            
        Returns:
            AITopicAnalysisResponse: Tópicos analisados pela IA
            
        Raises:
            Exception: Se a IA falhar após todas as tentativas
        """
        analysis_start = time.time()
        
        with LogContext(phase="topic_analysis", user_contest_id=user_contest_id) as phase_logger:
            phase_logger.info(
                "Starting topic analysis phase",
                topics_count=len(topics_data.topics_data_for_ai)
            )
            
            # Preparar entrada para a IA
            prompt_input = {
                "topics_json": json.dumps(topics_data.topics_data_for_ai, indent=2)
            }
            
            # Executar análise com validação e auto-correção
            ai_response_obj = self._invoke_ai_with_validation(
                prompt_input=prompt_input,
                topics_data=topics_data,
                user_contest_id=user_contest_id
            )
            
            analysis_duration = round((time.time() - analysis_start) * 1000, 2)
            
            # Log estatísticas da análise
            priority_counts = self._count_priorities(ai_response_obj)
            
            phase_logger.info(
                "Topic analysis phase completed",
                duration_ms=analysis_duration,
                analyzed_topics_count=len(ai_response_obj.analyzed_topics),
                priority_distribution=priority_counts
            )
            
            return ai_response_obj
            
    def _invoke_ai_with_validation(
        self,
        prompt_input: dict,
        topics_data: TopicsData,
        user_contest_id: int
    ) -> AITopicAnalysisResponse:
        """
        Invoca a IA com ciclo de validação e auto-correção.
        
        Args:
            prompt_input: Dados de entrada para o prompt
            topics_data: Dados dos tópicos (para validação)
            user_contest_id: ID do contest do usuário
            
        Returns:
            AITopicAnalysisResponse: Resposta validada da IA
        """
        from app.study.ai_validation_service import AIValidationService
        
        validation_service = AIValidationService(
            ai_service=self.ai_service,
            max_retries=AIConstants.MAX_RETRIES_AI_VALIDATION
        )
        
        # Função de validação específica para análise de tópicos
        def validate_analysis_response(response: AITopicAnalysisResponse) -> List[str]:
            input_topic_ids = {topic['topic_id'] for topic in topics_data.topics_data_for_ai}
            return ValidationOrchestrator.validate_analysis_phase_output(
                analysis_response=response,
                input_topic_ids=input_topic_ids,
                user_contest_id=user_contest_id
            )
        
        return validation_service.invoke_with_validation(
            prompt_template=topic_analysis_prompt,
            prompt_input=prompt_input,
            response_schema=AITopicAnalysisResponse,
            validation_function=validate_analysis_response,
            context={"phase": "topic_analysis", "user_contest_id": user_contest_id}
        )
        
    def _count_priorities(self, analysis_response: AITopicAnalysisResponse) -> dict:
        """
        Conta a distribuição de prioridades para logs.
        
        Args:
            analysis_response: Resposta da análise
            
        Returns:
            dict: Contagem de prioridades
        """
        priority_counts = {}
        for topic in analysis_response.analyzed_topics:
            priority = topic.priority_level
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        return priority_counts
