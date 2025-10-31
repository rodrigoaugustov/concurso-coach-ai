# backend/tests/unit/test_study/test_validators_integration.py

from app.core.validators import ValidationOrchestrator
from app.study.ai_schemas import AITopicAnalysisResponse, AnalyzedTopicData, AIStudyPlanResponse, StudySession


def test_analysis_validator_combines_errors():
    input_ids = {1, 2, 3}
    # Missing 3 and inventing 4; also invalid sessions for topic 2
    resp = AITopicAnalysisResponse(
        analyzed_topics=[
            AnalyzedTopicData(topic_id=1, priority_level="HIGH", estimated_sessions=1, prerequisite_topic_ids=[]),
            AnalyzedTopicData(topic_id=2, priority_level="HIGH", estimated_sessions=0, prerequisite_topic_ids=[]),
            AnalyzedTopicData(topic_id=4, priority_level="LOW", estimated_sessions=1, prerequisite_topic_ids=[]),
        ]
    )
    errors = ValidationOrchestrator.validate_analysis_phase_output(resp, input_ids, user_contest_id=99)
    assert errors and any("Tópicos" in e or "Sessões" in e or "diversidade" in e for e in errors)


def test_organization_validator_checks_limit_and_completeness():
    input_ids = {1, 2}
    plan = AIStudyPlanResponse(
        roadmap=[
            StudySession(session_number=1, summary="", priority_level="HIGH", priority_reason="", topic_ids=[1, 2, 3]),
            StudySession(session_number=2, summary="", priority_level="LOW", priority_reason="", topic_ids=[]),
            StudySession(session_number=3, summary="", priority_level="LOW", priority_reason="", topic_ids=[1]),
        ]
    )
    errors = ValidationOrchestrator.validate_organization_phase_output(plan, input_ids, max_sessions=2, user_contest_id=99)
    assert errors and ("excede o limite" in " ".join(errors) or "não incluiu" in " ".join(errors))
