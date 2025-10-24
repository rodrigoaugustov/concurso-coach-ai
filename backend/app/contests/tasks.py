# Em backend/app/contests/tasks.py

import json
import base64
from google.cloud import storage
from sqlalchemy.orm import Session

from app.celery_worker import celery_app
from app.core.database import SessionLocal
from app.core.settings import settings
from app.core.exceptions import AIValidationError
from .models import PublishedContest, ContestStatus
from .prompts import edict_extraction_prompt, subject_refinement_prompt
from . import crud
from app.core.ai_service import LangChainService
from app.contests.ai_schemas import EdictExtractionResponse

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
    print(f"Iniciando tarefa de processamento para o concurso ID: {contest_id}")
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
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        print("Download concluído.")

        # === ETAPA 1: EXTRAÇÃO BRUTA (IA) ===
        ai_service = LangChainService(
            provider="google",
            api_key=settings.GEMINI_API_KEY,
            model_name="gemini-2.5-flash",
            temperature=1.0 # Para ter liberdade criativa na inferência das matérias
        )

        # 2. Monta as partes do conteúdo para a chamada multimodal
        content_parts=[
                # Parte 1: Texto (prompt)
                {"type": "text", "text": edict_extraction_prompt},
                # Parte 2: Dados binários (PDF)
                {"type": "file", "data": pdf_base64, "mime_type": "application/pdf",  "source_type": "base64"}
                ]

        # 3. Chama o novo método do serviço LangChain
        initial_response_obj = ai_service.generate_structured_output_from_content(
            content_parts=content_parts,
            response_schema=EdictExtractionResponse
        )

        initial_data_dict = initial_response_obj.dict()
        initial_data_json_str = json.dumps(initial_data_dict, indent=2, default=str, ensure_ascii=False)
        print("Pipeline de Extração - Etapa 1: Concluída.")

        # === ETAPA 2: REFINAMENTO DOS SUBJECTS (IA) ===
        print("Pipeline de Extração - Etapa 2: Refinando a categorização das matérias...")

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
        print("Pipeline de Extração - Etapa 2: Concluída.")

        # A resposta já é um objeto Pydantic, convertemos para dict
        extracted_data = refined_data_dict
        print(extracted_data)

            # === NOVA ETAPA DE VALIDAÇÃO DETERMINÍSTICA ===
        print("Pipeline de Extração - Validação: Verificando consistência dos tópicos...")
        
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

            # Compara os dois conjuntos
            if initial_topics != refined_topics:
                missing_from_refined = initial_topics - refined_topics
                added_in_refined = refined_topics - initial_topics
                
                error_messages = []
                if missing_from_refined:
                    error_messages.append(f"IA de refinamento removeu tópicos: {missing_from_refined}")
                if added_in_refined:
                    error_messages.append(f"IA de refinamento inventou tópicos: {added_in_refined}")
                
                # Levanta um erro de IA específico para acionar a retentativa do Celery
                raise AIValidationError(error_messages)

            print("Pipeline de Extração - Validação: Consistência dos tópicos OK.")
        except Exception as e:
            # Se a validação falhar, usamos a extração inicial como fallback
            # e logamos o erro para análise posterior.
            print(f"AVISO: A etapa de refinamento da IA falhou na validação ({e}). Usando os dados da extração inicial.")
            extracted_data = initial_data_dict


        # === ETAPA 3: PERSISTÊNCIA NO BANCO ===
        print("Pipeline de Extração - Etapa 3: Salvando dados refinados no banco...")
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
