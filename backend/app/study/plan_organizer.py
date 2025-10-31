# backend/app/study/plan_organizer.py (usar validadores centralizados)

"""
StudyPlanOrganizer: Responsável pela organização final do plano de estudos.
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
    def __init__(self, ai_service: LangChainService):
        self.ai_service = ai_service
        self.logger = get_logger("study.plan_organizer")
        
    def organize_plan(self, analysis: AITopicAnalysisResponse, total_sessions: int, input_topic_ids: Set[int], user_contest_id: int) -> AIStudyPlanResponse:
        organization_start = time.time()
        with LogContext(phase="plan_organization", user_contest_id=user_contest_id) as phase_logger:
            analyzed_data = analysis.dict()
            prompt_input = {
                "total_sessions": total_sessions,
                "analyzed_topics_json": json.dumps(analyzed_data, indent=2),
            }
            final_plan_obj = self._invoke_ai_with_validation(
                prompt_input=prompt_input,
                total_sessions=total_sessions,
                input_topic_ids=input_topic_ids,
                user_contest_id=user_contest_id,
            )
            phase_logger.info(
                "Plan organization phase completed",
                duration_ms=round((time.time() - organization_start) * 1000, 2),
                roadmap_sessions_count=len(final_plan_obj.roadmap),
            )
            return final_plan_obj

    def _invoke_ai_with_validation(self, prompt_input: dict, total_sessions: int, input_topic_ids: Set[int], user_contest_id: int) -> AIStudyPlanResponse:
        from app.study.ai_validation_service import AIValidationService
        validation_service = AIValidationService(ai_service=self.ai_service, max_retries=AIConstants.MAX_RETRIES_AI_VALIDATION)

        def validate_plan_response(response: AIStudyPlanResponse) -> List[str]:
            return ValidationOrchestrator.validate_organization_phase_output(
                plan_response=response,
                input_topic_ids=input_topic_ids,
                max_sessions=total_sessions,
                user_contest_id=user_contest_id,
            )

        return validation_service.invoke_with_validation(
            prompt_template=plan_organization_prompt,
            prompt_input=prompt_input,
            response_schema=AIStudyPlanResponse,
            validation_function=validate_plan_response,
            context={"phase": "plan_organization", "user_contest_id": user_contest_id},
        )
