# backend/tests/unit/test_contests/test_edict_processor.py

import json
import types
from unittest.mock import MagicMock

from app.contests.edict_processor import EdictProcessor


def _make_db(contest):
    db = MagicMock()
    db.query().filter().first.return_value = contest
    return db


def test_edict_processor_happy_path(mocker):
    contest = types.SimpleNamespace(id=1, status=types.SimpleNamespace(value="PENDING"), file_url="https://storage.googleapis.com/bucket/file.pdf")
    db = _make_db(contest)

    # Mock GCS client
    mock_client = mocker.patch("app.contests.edict_processor.storage.Client")
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_blob.download_as_bytes.return_value = b"%PDF-1.4..."
    mock_bucket.blob.return_value = mock_blob
    mock_client.return_value.bucket.return_value = mock_bucket

    # Mock AI service methods
    mocker.patch("app.contests.edict_processor.LangChainService.generate_structured_output_from_content", return_value=types.SimpleNamespace(dict=lambda: {"contest_roles": []}))
    mocker.patch("app.contests.edict_processor.LangChainService.generate_structured_output", return_value=types.SimpleNamespace(dict=lambda: {"contest_roles": []}))

    # Mock persistence
    mock_save = mocker.patch("app.contests.edict_processor.crud.save_structured_edict_data")

    processor = EdictProcessor(db=db, contest_id=1)
    result = processor.process()

    assert "concluído" in result
    mock_save.assert_called_once()
