# Em backend/app/contests/tasks.py

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

# Logger para tasks do Celery
logger = get_logger("contests.tasks")

@celery_app.task(
    name="process_edict_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=5,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True
)
def process_edict_task(self, contest_id: int):
    """
    Tarefa assíncrona para processar um edital, com lógica de retentativa.
    """
    task_start_time = time.time()
    
    # Context para logs estruturados desta task
    with LogContext(task_name="process_edict", contest_id=contest_id, attempt=self.request.retries + 1) as task_logger:
        task_logger.info("Starting edict processing task")
        
        db: Session = SessionLocal()
        contest = db.query(PublishedContest).filter(PublishedContest.id == contest_id).first()
        
        if not contest:
            task_logger.error("Contest not found - task will not retry", contest_id=contest_id)
            return

        try:
            # Só atualiza o status se a tarefa ainda estiver pendente
            if contest.status == ContestStatus.PENDING:
                task_logger.info(
                    "Updating contest status to PROCESSING",
                    contest_name=contest.name,
                    previous_status=contest.status.value
                )
                contest.status = ContestStatus.PROCESSING
                db.commit()

            # === ETAPA 1: DOWNLOAD DO ARQUIVO ===
            download_start = time.time()
            task_logger.info("Starting file download from GCS", file_url=contest.file_url)
            
            try:
                storage_client = storage.Client(project=settings.GCP_PROJECT_ID)
                bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
                blob_name = contest.file_url.replace(f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/", "")
                blob = bucket.blob(blob_name)
                pdf_content = blob.download_as_bytes()
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                
                download_duration = round((time.time() - download_start) * 1000, 2)
                file_size_mb = round(len(pdf_content) / (1024 * 1024), 2)
                
                task_logger.info(
                    "File download completed",
                    duration_ms=download_duration,
                    file_size_mb=file_size_mb,
                    blob_name=blob_name
                )
                
            except Exception as e:
                task_logger.error(
                    "File download failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    file_url=contest.file_url
                )
                raise

            # === ETAPA 2: EXTRAÇÃO BRUTA (IA) ===
            extraction_start = time.time()
            task_logger.info("Starting AI extraction phase")
            
            try:
                ai_service = LangChainService(
                    provider="google",
                    api_key=settings.GEMINI_API_KEY,
                    model_name="gemini-2.5-flash",
                    temperature=1.0 # Para ter liberdade criativa na inferência das matérias
                )

                # Monta as partes do conteúdo para a chamada multimodal
                content_parts=[
                    # Parte 1: Texto (prompt)
                    {"type": "text", "text": edict_extraction_prompt},
                    # Parte 2: Dados binários (PDF)
                    {"type": "file", "data": pdf_base64, "mime_type": "application/pdf", "source_type": "base64"}
                ]

                # Chama o novo método do serviço LangChain
                initial_response_obj = ai_service.generate_structured_output_from_content(
                    content_parts=content_parts,
                    response_schema=EdictExtractionResponse
                )

                initial_data_dict = initial_response_obj.dict()
                initial_data_json_str = json.dumps(initial_data_dict, indent=2, default=str, ensure_ascii=False)
                
                extraction_duration = round((time.time() - extraction_start) * 1000, 2)
                
                # Conta quantos roles e topics foram extraídos
                roles_count = len(initial_data_dict.get("contest_roles", []))
                topics_count = sum(
                    len(role.get("programmatic_content", []))
                    for role in initial_data_dict.get("contest_roles", [])
                )
                
                task_logger.info(
                    "AI extraction phase completed",
                    duration_ms=extraction_duration,
                    roles_extracted=roles_count,
                    topics_extracted=topics_count
                )
                
            except Exception as e:
                task_logger.error(
                    "AI extraction phase failed",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise

            # === ETAPA 3: REFINAMENTO DOS SUBJECTS (IA) ===
            refinement_start = time.time()
            task_logger.info("Starting AI refinement phase")
            
            try:
                # Passa a string JSON diretamente para o prompt.
                refinement_prompt_input = {
                    "extracted_json": initial_data_json_str
                }

                # A chamada aqui usa o método de texto, pois o input é um JSON em texto
                refined_response_obj = ai_service.generate_structured_output(
                    prompt_template=subject_refinement_prompt,
                    prompt_input=refinement_prompt_input,
                    response_schema=EdictExtractionResponse # Esperamos a mesma estrutura de volta!
                )

                refined_data_dict = refined_response_obj.dict()
                
                refinement_duration = round((time.time() - refinement_start) * 1000, 2)
                
                task_logger.info(
                    "AI refinement phase completed",
                    duration_ms=refinement_duration
                )
                
            except Exception as e:
                task_logger.error(
                    "AI refinement phase failed",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise

            # A resposta já é um objeto Pydantic, convertemos para dict
            extracted_data = refined_data_dict

            # === ETAPA 4: VALIDAÇÃO DETERMINÍSTICA ===
            validation_start = time.time()
            task_logger.info("Starting deterministic validation")
            
            try:
                # Extrai um conjunto de 'topic' names da extração inicial
                initial_topics = set()
                for role in initial_data_dict.get("contest_roles", []):
                    for content in role.get("programmatic_content", []):
                        initial_topics.add(content.get("topic"))

                # Extrai um conjunto de 'topic' names da resposta refinada
                refined_topics = set()
                for role in extracted_data.get("contest_roles", []):
                    for content in role.get("programmatic_content", []):
                        refined_topics.add(content.get("topic"))

                validation_duration = round((time.time() - validation_start) * 1000, 2)
                
                # Compara os dois conjuntos
                if initial_topics != refined_topics:
                    missing_from_refined = initial_topics - refined_topics
                    added_in_refined = refined_topics - initial_topics
                    
                    error_messages = []
                    if missing_from_refined:
                        error_messages.append(f"IA de refinamento removeu tópicos: {missing_from_refined}")
                    if added_in_refined:
                        error_messages.append(f"IA de refinamento inventou tópicos: {added_in_refined}")
                    
                    task_logger.warning(
                        "Validation inconsistency detected - using initial extraction",
                        duration_ms=validation_duration,
                        missing_topics=list(missing_from_refined) if missing_from_refined else [],
                        added_topics=list(added_in_refined) if added_in_refined else [],
                        fallback_to_initial=True
                    )
                    
                    # Levanta um erro de IA específico para acionar a retentativa do Celery
                    raise AIValidationError(error_messages)

                task_logger.info(
                    "Deterministic validation passed",
                    duration_ms=validation_duration,
                    initial_topics_count=len(initial_topics),
                    refined_topics_count=len(refined_topics)
                )
                
            except AIValidationError:
                # Re-levanta o erro de validação para retry
                raise
            except Exception as e:
                # Se a validação falhar por outro motivo, usa a extração inicial como fallback
                task_logger.warning(
                    "Validation failed with unexpected error - using initial extraction",
                    error=str(e),
                    error_type=type(e).__name__,
                    fallback_to_initial=True
                )
                extracted_data = initial_data_dict

            # === ETAPA 5: PERSISTÊNCIA NO BANCO ===
            persistence_start = time.time()
            task_logger.info("Starting database persistence")
            
            try:
                crud.save_structured_edict_data(db=db, contest_id=contest_id, data=extracted_data)
                contest.status = ContestStatus.COMPLETED
                
                persistence_duration = round((time.time() - persistence_start) * 1000, 2)
                total_duration = round((time.time() - task_start_time) * 1000, 2)
                
                task_logger.info(
                    "Database persistence completed",
                    duration_ms=persistence_duration
                )
                
                task_logger.info(
                    "Edict processing task completed successfully",
                    total_duration_ms=total_duration,
                    final_status=contest.status.value
                )
                
            except Exception as e:
                task_logger.error(
                    "Database persistence failed",
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise

        except Exception as exc:
            # Nós o relançamos para que o Celery possa vê-lo e acionar o autoretry.
            max_retries = self.max_retries if self.max_retries is not None else 0
            current_attempt = self.request.retries + 1
            total_attempts = max_retries + 1
            
            task_logger.error(
                "Task execution failed",
                attempt=current_attempt,
                max_attempts=total_attempts,
                error=str(exc),
                error_type=type(exc).__name__,
                will_retry=(current_attempt < total_attempts)
            )
            
            # Antes da última tentativa, atualizamos o status para FAILED no banco
            if self.request.retries >= max_retries:
                task_logger.error(
                    "Maximum retry attempts reached - marking contest as FAILED",
                    final_attempt=True
                )
                contest.status = ContestStatus.FAILED
                contest.error_message = str(exc)
            
            raise self.retry(exc=exc)

        finally:
            db.commit()
            db.close()
            
    return f"Processamento do concurso {contest_id} concluído com sucesso."