# backend/app/contests/edict_processor.py

"""
EdictProcessor: Pipeline orientado a passos para processar editais.
Mantém a assinatura e políticas de retry na task; apenas delega a execução.
"""

import base64
import json
import time
from datetime import date
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.logging import LogContext, get_logger
from app.core.exceptions import AIValidationError
from app.core.ai_service import LangChainService
from app.contests.ai_schemas import EdictExtractionResponse
from app.contests import crud
from app.contests.models import PublishedContest, ContestStatus
from app.contests.prompts import edict_extraction_prompt, subject_refinement_prompt

logger = get_logger("contests.edict_processor")

def json_serializer(obj):
    """Serializador JSON para objetos não serializáveis por padrão."""
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

class EdictProcessor:
    def __init__(self, db: Session, contest_id: int):
        self.db = db
        self.contest_id = contest_id
        self.contest: PublishedContest | None = None
        self.ai_service: LangChainService | None = None

    def process(self) -> str:
        with LogContext(processor="edict", contest_id=self.contest_id) as log:
            try:
                self._setup(log)
                pdf_b64 = self._get_pdf_from_db(log)
                initial = self._extract_data(pdf_b64, log)
                refined = self._refine_data(initial, log)
                self._validate_data(initial, refined, log)
                self._persist_data(refined, log)
                self._mark_completed(log)
                return f"Processamento do concurso {self.contest_id} concluído"
            except Exception as exc:
                self._handle_error(exc, log)
                raise

    def _setup(self, log):
        self.contest = self.db.query(PublishedContest).filter(PublishedContest.id == self.contest_id).first()
        if not self.contest:
            raise ValueError("Contest not found")
        if self.contest.status == ContestStatus.PENDING:
            self.contest.status = ContestStatus.PROCESSING
            self.db.commit()
        self.ai_service = LangChainService(
            provider="google",
            api_key=settings.GEMINI_API_KEY,
            model_name="gemini-2.5-pro",
            temperature=1.0,
        )
        log.info("Setup completed", status=self.contest.status.value)

    def _get_pdf_from_db(self, log) -> str:
        t0 = time.time()
        if not self.contest.file_content:
            raise ValueError("Conteúdo do arquivo não encontrado no banco de dados.")
        
        pdf_content = self.contest.file_content
        pdf_base64 = base64.b64encode(pdf_content).decode("utf-8")
        log.info("PDF loaded from DB", ms=round((time.time()-t0)*1000,2), size_mb=round(len(pdf_content)/(1024*1024),2))
        return pdf_base64

    def _extract_data(self, pdf_b64: str, log) -> Dict[str, Any]:
        t0 = time.time()
        content_parts = [
            {"type": "text", "text": edict_extraction_prompt},
            {"type": "file", "data": pdf_b64, "mime_type": "application/pdf", "source_type": "base64"},
        ]
        resp = self.ai_service.generate_structured_output_from_content(
            content_parts=content_parts, response_schema=EdictExtractionResponse
        )
        data = resp.dict()
        print(data)
        log.info("Extraction completed", ms=round((time.time()-t0)*1000,2))
        return data

    def _refine_data(self, initial: Dict[str, Any], log) -> Dict[str, Any]:
        t0 = time.time()
        refined = self.ai_service.generate_structured_output(
            prompt_template=subject_refinement_prompt,
            prompt_input={"extracted_json": json.dumps(initial, indent=2, ensure_ascii=False, default=json_serializer)},
            response_schema=EdictExtractionResponse,
        )
        data = refined.dict()
        log.info("Refinement completed", ms=round((time.time()-t0)*1000,2))
        return data

    def _validate_data(self, initial: Dict[str, Any], refined: Dict[str, Any], log):
        t0 = time.time()
        initial_topics = {c.get("topic") for r in initial.get("contest_roles", []) for c in r.get("programmatic_content", [])}
        refined_topics = {c.get("topic") for r in refined.get("contest_roles", []) for c in r.get("programmatic_content", [])}
        if initial_topics != refined_topics:
            missing = initial_topics - refined_topics
            added = refined_topics - initial_topics
            log.warning("Validation inconsistency", missing=list(missing), added=list(added), fallback=True)
            raise AIValidationError([
                f"IA de refinamento removeu tópicos: {missing}" if missing else "",
                f"IA de refinamento inventou tópicos: {added}" if added else "",
            ])
        log.info("Validation passed", ms=round((time.time()-t0)*1000,2))

    def _persist_data(self, data: Dict[str, Any], log):
        t0 = time.time()
        crud.save_structured_edict_data(db=self.db, contest_id=self.contest_id, data=data)
        log.info("Persistence completed", ms=round((time.time()-t0)*1000,2))

    def _mark_completed(self, log):
        self.contest.status = ContestStatus.COMPLETED
        self.db.commit()
        log.info("Contest marked completed", status=self.contest.status.value)

    def _handle_error(self, exc: Exception, log):
        log.error("Processor failed", error=str(exc), error_type=type(exc).__name__)