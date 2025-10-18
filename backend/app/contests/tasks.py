# Em backend/app/contests/tasks.py

import json
from google.cloud import storage
from sqlalchemy.orm import Session

from app.celery_worker import celery_app
from app.core.database import SessionLocal
from app.core.settings import settings
from app.core import ai_service
from .models import PublishedContest, ContestStatus
from .prompts import edict_extraction_prompt
from . import crud

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
    db: Session = SessionLocal()
    contest = db.query(PublishedContest).filter(PublishedContest.id == contest_id).first()
    
    if not contest:
        print(f"ERRO: Concurso com ID {contest_id} não encontrado. Não será tentado novamente.")
        return

    try:
        # Só atualiza o status se a tarefa ainda estiver pendente
        if contest.status == ContestStatus.PENDING:
            print(f"Iniciando processamento do concurso: {contest.name} (ID: {contest.id})")
            contest.status = ContestStatus.PROCESSING
            db.commit()

        # --- A LÓGICA DE NEGÓCIO FICA DENTRO DO TRY ---
        print(f"Baixando arquivo do GCS: {contest.file_url}")
        storage_client = storage.Client(project=settings.GCP_PROJECT_ID)
        bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
        blob_name = contest.file_url.replace(f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/", "")
        blob = bucket.blob(blob_name)
        pdf_content = blob.download_as_bytes()
        print("Download concluído.")

        # =================================================================
        # DESCOMENTE A LINHA ABAIXO PARA TESTAR A RETENTATIVA
        # raise ValueError("Forçando um erro para testar o retry!")
        # =================================================================

        structured_data_str = ai_service.extract_edict_data_from_pdf(
            pdf_content=pdf_content,
            prompt=edict_extraction_prompt
        )
        
        print("\n--- DADOS EXTRAÍDOS PELA IA ---")
        print(structured_data_str)
        print("--------------------------------\n")
        
        extracted_data = json.loads(structured_data_str)
        crud.save_structured_edict_data(db=db, contest_id=contest_id, data=extracted_data)
        
        contest.status = ContestStatus.COMPLETED
        print(f"Processamento do concurso (ID: {contest.id}) finalizado com sucesso!")

    except Exception as exc:
        # Nós o relançamos para que o Celery possa vê-lo e acionar o autoretry.
        max_retries = self.max_retries if self.max_retries is not None else 0
        print(f"ERRO na tentativa {self.request.retries + 1} de {max_retries + 1}: {exc}")
        
        # Antes da última tentativa, atualizamos o status para FAILED no banco
        if self.request.retries >= max_retries:
            print("Número máximo de tentativas atingido. Marcando como FAILED.")
            contest.status = ContestStatus.FAILED
            contest.error_message = str(exc)
        
        raise self.retry(exc=exc)

    finally:
        db.commit()
        db.close()
        
    return f"Processamento do concurso {contest_id} concluído com sucesso."