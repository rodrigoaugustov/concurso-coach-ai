# backend/app/study/topic_analyzer.py (usar validadores centralizados)

"""
StudyTopicAnalyzer: Responsável pela análise de tópicos via IA.
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
    def __init__(self, ai_service: LangChainService):
        self.ai_service = ai_service
        self.logger = get_logger("study.topic_analyzer")
        
    def analyze_topics(self, topics_data: TopicsData, user_contest_id: int) -> AITopicAnalysisResponse:
        analysis_start = time.time()
        with LogContext(phase="topic_analysis", user_contest_id=user_contest_id) as phase_logger:
            prompt_input = {"topics_json": json.dumps(topics_data.topics_data_for_ai, indent=2)}
            ai_response_obj = self._invoke_ai_with_validation(
                prompt_input=prompt_input,
                topics_data=topics_data,
                user_contest_id=user_contest_id,
            )
            phase_logger.info(
                "Topic analysis phase completed",
                duration_ms=round((time.time() - analysis_start) * 1000, 2),
                analyzed_topics_count=len(ai_response_obj.analyzed_topics),
            )
            return ai_response_obj

    def _invoke_ai_with_validation(self, prompt_input: dict, topics_data: TopicsData, user_contest_id: int) -> AITopicAnalysisResponse:
        from app.study.ai_validation_service import AIValidationService
        validation_service = AIValidationService(ai_service=self.ai_service, max_retries=AIConstants.MAX_RETRIES_AI_VALIDATION)

        def validate_analysis_response(response: AITopicAnalysisResponse) -> List[str]:
            input_topic_ids = {topic['topic_id'] for topic in topics_data.topics_data_for_ai}
            return ValidationOrchestrator.validate_analysis_phase_output(
                analysis_response=response,
                input_topic_ids=input_topic_ids,
                user_contest_id=user_contest_id,
            )

        return validation_service.invoke_with_validation(
            prompt_template=topic_analysis_prompt,
            prompt_input=prompt_input,
            response_schema=AITopicAnalysisResponse,
            validation_function=validate_analysis_response,
            context={"phase": "topic_analysis", "user_contest_id": user_contest_id},
        )
