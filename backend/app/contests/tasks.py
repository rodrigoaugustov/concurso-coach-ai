# Em backend/app/contests/tasks.py (delegar para EdictProcessor)

import json
import base64
import time
from google.cloud import storage
from sqlalchemy.orm import Session

from app.celery_worker import celery_app
from app.core.database import SessionLocal
from app.core.settings import settings
from app.core.exceptions import AIValidationError
from app.core.logging import get_logger, LogContext
from .models import PublishedContest, ContestStatus
from .prompts import edict_extraction_prompt, subject_refinement_prompt
from . import crud
from app.core.ai_service import LangChainService
from app.contests.ai_schemas import EdictExtractionResponse
from app.core.constants import CeleryConstants, AIConstants
from app.contests.edict_processor import EdictProcessor

# Logger para tasks do Celery
logger = get_logger("contests.tasks")

@celery_app.task(
    name="process_edict_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': CeleryConstants.MAX_RETRIES},
    retry_backoff=CeleryConstants.RETRY_BACKOFF_SECONDS,
    soft_time_limit=CeleryConstants.SOFT_TIME_LIMIT_SECONDS,
    time_limit=CeleryConstants.HARD_TIME_LIMIT_SECONDS,
    acks_late=True
)
def process_edict_task(self, contest_id: int):
    task_start_time = time.time()
    with LogContext(task_name="process_edict", contest_id=contest_id, attempt=self.request.retries + 1) as task_logger:
        db: Session = SessionLocal()
        try:
            processor = EdictProcessor(db=db, contest_id=contest_id)
            result = processor.process()
            total_duration = round((time.time() - task_start_time) * 1000, 2)
            task_logger.info("Edict processing task completed successfully", total_duration_ms=total_duration)
            return result
        except Exception as exc:
            max_retries = self.max_retries if self.max_retries is not None else 0
            current_attempt = self.request.retries + 1
            total_attempts = max_retries + 1
            task_logger.error("Task execution failed", attempt=current_attempt, max_attempts=total_attempts, error=str(exc), error_type=type(exc).__name__, will_retry=(current_attempt < total_attempts))
            raise self.retry(exc=exc)
        finally:
            db.commit()
            db.close()
