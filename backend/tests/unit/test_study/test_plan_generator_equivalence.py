# backend/tests/unit/test_study/test_plan_generator_equivalence.py

import types
from unittest.mock import MagicMock

from app.study.plan_generator import StudyPlanGenerator


def _make_db_with_topics(topics=3):
    db = MagicMock()
    # Mock ProgrammaticContent and UserTopicProgress join query used by collector
    # Keep it minimal; collector relies on .all() returning iterable of (topic, proficiency)
    Topic = types.SimpleNamespace
    topic_rows = []
    for i in range(1, topics+1):
        topic = Topic(id=i, exam_module="M", subject="S", topic=f"T{i}")
        topic_rows.append((topic, 0.5))
    db.query().join().filter().all.return_value = topic_rows

    # Mock ExamStructure query for impact map
    structure = types.SimpleNamespace(number_of_questions=10, weight_per_question=1.0, level_type=types.SimpleNamespace(value="SUBJECT"), level_name="S")
    db.query().filter().all.side_effect = [
        [structure],   # first call for ExamStructure
        []             # second call placeholder if any other .all is hit
    ]

    # Mock StudyRoadmapSession persistence path: add_all/commit
    db.add_all = MagicMock()
    db.commit = MagicMock()

    return db


def _make_user_contest():
    role = types.SimpleNamespace(contest=types.SimpleNamespace(name="C", exam_date=types.SimpleNamespace(__sub__=None)))
    # provide date diff via custom .exam_date
    import datetime
    exam_date = datetime.date.today() + datetime.timedelta(days=2)
    role.contest.exam_date = exam_date
    user_contest = types.SimpleNamespace(id=1, user_id=123, role=role, contest_role_id=10)
    return user_contest


def test_plan_generator_runs_with_refactored_pipeline(mocker):
    db = _make_db_with_topics(2)
    user_contest = _make_user_contest()

    # Mock AI services used by analyzer/organizer to return minimal valid schemas
    from app.study.ai_schemas import AITopicAnalysisResponse, AnalyzedTopicData, AIStudyPlanResponse, StudySession

    mock_analysis = AITopicAnalysisResponse(
        analyzed_topics=[
            AnalyzedTopicData(topic_id=1, priority_level="HIGH", estimated_sessions=1, prerequisite_topic_ids=[]),
            AnalyzedTopicData(topic_id=2, priority_level="LOW", estimated_sessions=1, prerequisite_topic_ids=[]),
        ]
    )
    mock_plan = AIStudyPlanResponse(
        roadmap=[
            StudySession(session_number=1, summary="s", priority_level="HIGH", priority_reason="r", topic_ids=[1]),
            StudySession(session_number=2, summary="s", priority_level="LOW", priority_reason="r", topic_ids=[2]),
        ]
    )

    mocker.patch("app.study.topic_analyzer.StudyTopicAnalyzer._invoke_ai_with_validation", return_value=mock_analysis)
    mocker.patch("app.study.plan_organizer.StudyPlanOrganizer._invoke_ai_with_validation", return_value=mock_plan)

    gen = StudyPlanGenerator(db=db, user_contest=user_contest)
    result = gen.generate()

    assert result["status"] == "success"
    assert result["roadmap_items_created"] == 2
    db.add_all.assert_called_once()
    db.commit.assert_called_once()
