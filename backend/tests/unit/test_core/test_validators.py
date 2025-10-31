# backend/tests/unit/test_core/test_validators.py

from app.core.validators import TopicValidators, StudyPlanValidators
from app.study.ai_schemas import AIStudyPlanResponse, StudySession


def test_validate_topic_completeness_detects_missing_and_extra():
    input_ids = {1, 2, 3}
    output_ids = {2, 3, 4}
    errors = TopicValidators.validate_topic_completeness(input_ids, output_ids)
    assert any("ausentes" in e or "inventados" in e for e in errors)


def test_validate_session_limit_blocks_overflow():
    plan = AIStudyPlanResponse(roadmap=[
        StudySession(session_number=i, summary="", priority_level="LOW", priority_reason="", topic_ids=[1])
        for i in range(1, 6)
    ])
    errors = StudyPlanValidators.validate_session_limit(plan, max_sessions=4)
    assert errors and "excede o limite" in errors[0]
