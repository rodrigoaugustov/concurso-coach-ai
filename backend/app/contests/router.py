import uuid
import hashlib
from typing import Annotated, List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from google.cloud import storage
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.settings import settings
from app.users.auth import get_current_user
from app.users import schemas as user_schemas # Importa os schemas de usuário com um apelido
from . import crud
from . import schemas as contest_schemas # Importa os schemas de concurso com um apelido
from .tasks import process_edict_task # Importa a tarefa assíncrona


router = APIRouter()

@router.post("/upload", response_model=contest_schemas.Contest, status_code=status.HTTP_201_CREATED)
def upload_contest_edict(
    file: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
    current_user: user_schemas.User = Depends(get_current_user) # Endpoint protegido!
):
    """
    Recebe um arquivo PDF de edital e um nome para o concurso.
    1. Calcula o hash do arquivo para evitar duplicatas.
    2. Faz o upload do arquivo para o Google Cloud Storage.
    3. Cria um registro do concurso no banco de dados com status PENDING.
    """
    try:
        # 1. Ler conteúdo e calcular hash
        contents = file.file.read()
        file_hash = hashlib.sha256(contents).hexdigest()
        file.file.seek(0) # Retorna o "cursor" do arquivo para o início

        existing_contest = crud.get_contest_by_hash(db, file_hash=file_hash)
        if existing_contest:
            return existing_contest

        # 2. Fazer upload para o GCS
        storage_client = storage.Client(project=settings.GCP_PROJECT_ID)
        bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
        
        # Gera um nome de arquivo único para evitar conflitos
        file_extension = file.filename.split('.')[-1]
        blob_name = f"edicts/{uuid.uuid4()}.{file_extension}"
        blob = bucket.blob(blob_name)
        
        blob.upload_from_file(file.file, content_type=file.content_type)
        
        # 3. Criar registro no banco de dados
        db_contest = crud.create_contest(
            db=db,
            name=file.filename,
            file_url=blob.public_url,
            file_hash=file_hash
        )

        # 4. DISPARAR A TAREFA ASSÍNCRONA
        process_edict_task.delay(db_contest.id)

        return db_contest

    except Exception as e:
        # Em caso de qualquer erro, retorna uma exceção HTTP
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    

@router.post("/{contest_id}/reprocess", response_model=contest_schemas.Contest, summary="Reprocess a failed contest")
def reprocess_contest(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user: user_schemas.User = Depends(get_current_user) # Protegido!
):
    """
    Pega um concurso que falhou, redefine seu status para PENDING e 
    dispara a tarefa de processamento assíncrono novamente.
    """
    contest = db.query(crud.models.PublishedContest).filter(crud.models.PublishedContest.id == contest_id).first()

    if not contest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contest not found")

    if contest.status != crud.models.ContestStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Contest is not in FAILED state. Current state: {contest.status.name}"
        )

    # Reseta o status e a mensagem de erro
    contest.status = crud.models.ContestStatus.PENDING
    contest.error_message = None
    db.commit()
    db.refresh(contest)

    # Dispara a tarefa novamente
    from .tasks import process_edict_task
    process_edict_task.delay(contest.id)
    
    print(f"Reprocessing requested for contest ID: {contest.id}")
    return contest

@router.get("/", response_model=List[contest_schemas.Contest], summary="List all available contests")
def list_available_contests(
    db: Session = Depends(get_db)
):
    """
    Retorna uma lista de todos os concursos que foram processados com sucesso
    e estão disponíveis para os usuários se inscreverem.
    """
    contests = db.query(crud.models.PublishedContest).filter(
        crud.models.PublishedContest.status == crud.models.ContestStatus.COMPLETED
    ).all()
    return contests
