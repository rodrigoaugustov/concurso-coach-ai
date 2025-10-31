# backend/tests/unit/test_core/test_constants.py

import importlib


def test_constants_have_expected_values():
    constants = importlib.import_module("app.core.constants")

    assert constants.CeleryConstants.MAX_RETRIES == 3
    assert constants.CeleryConstants.RETRY_BACKOFF_SECONDS == 5
    assert constants.CeleryConstants.SOFT_TIME_LIMIT_SECONDS == 300
    assert constants.CeleryConstants.HARD_TIME_LIMIT_SECONDS == 600

    assert constants.AIConstants.TEMPERATURE_CREATIVE == 1.0
    assert constants.AIConstants.TEMPERATURE_BALANCED == 0.5
    assert constants.ValidationConstants.MAX_SESSIONS_ESTIMATE == 10
    assert constants.ValidationConstants.SESSIONS_PER_DAY == 2
