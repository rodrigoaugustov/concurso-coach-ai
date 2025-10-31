# backend/tests/unit/test_contests/test_tasks_delegation.py

from unittest.mock import MagicMock
import types
import time

from app.contests.tasks import process_edict_task


def test_process_edict_task_delegates_to_processor(mocker):
    # Patch EdictProcessor
    mock_processor_cls = mocker.patch("app.contests.tasks.EdictProcessor")
    mock_instance = MagicMock()
    mock_instance.process.return_value = "ok"
    mock_processor_cls.return_value = mock_instance

    # Build celery self mock
    class Self:
        request = types.SimpleNamespace(retries=0)
        max_retries = 0
        def retry(self, exc):
            raise exc
    
    result = process_edict_task(Self(), 123)
    assert result == "ok"
    mock_processor_cls.assert_called_once()
    mock_instance.process.assert_called_once()
