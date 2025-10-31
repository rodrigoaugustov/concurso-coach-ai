from __future__ import annotations
from typing import Dict, Any
import time
from contextlib import contextmanager
from app.core.logging import get_logger

logger = get_logger("analytics")

@contextmanager
def interaction_timer(context: Dict[str, Any]):
    start = time.time()
    try:
        yield
    finally:
        duration_ms = round((time.time() - start) * 1000, 2)
        logger.info("chat_interaction_completed", **{**context, "duration_ms": duration_ms})
