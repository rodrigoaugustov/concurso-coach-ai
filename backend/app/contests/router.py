import hashlib
from typing import Annotated, List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.users.auth import get_current_user
from app.users import schemas as user_schemas
from . import crud
from . import schemas as contest_schemas
from .tasks import process_edict_task
from app.core.security import InputValidator, MAX_FILE_SIZE_MB

# Rate limiting (decorator) - optional if slowapi available
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
except Exception:
    limiter = None

router = APIRouter()


def _enforce_pdf_validation(upload: UploadFile) -> bytes:
    contents = upload.file.read()
    ok, err = InputValidator.validate_pdf_file(contents, upload.filename or "edital.pdf")
    upload.file.seek(0)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE",
                "message": err or "Arquivo inválido",
                "details": {"allowed_type": "PDF", "max_size_mb": MAX_FILE_SIZE_MB},
            },
        )
    return contents


# Apply 5/min per IP if limiter exists
limit_decorator = (limiter.limit("5/minute") if limiter else (lambda f: f))


@router.post("/upload", response_model=contest_schemas.Contest, status_code=status.HTTP_201_CREATED)
@limit_decorator
def upload_contest_edict(
    request: Request,
    file: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
    current_user: user_schemas.User = Depends(get_current_user),
):
    """
    Upload seguro de PDF de edital com validação por magic bytes, tamanho e sanitização de filename.
    Evita duplicatas por hash de conteúdo e salva o arquivo no banco de dados.
    """
    try:
        # 1) Validação completa do arquivo
        contents = _enforce_pdf_validation(file)
        file_hash = hashlib.sha256(contents).hexdigest()

        existing_contest = crud.get_contest_by_hash(db, file_hash=file_hash)
        if existing_contest:
            return existing_contest

        # 2) Sanitização do nome do arquivo
        safe_original = InputValidator.sanitize_filename(file.filename or "edital.pdf")

        # 3) Persistir e disparar processamento
        db_contest = crud.create_contest(
            db=db,
            name=safe_original,
            file_hash=file_hash,
            file_content=contents,
        )

        process_edict_task.delay(db_contest.id)
        return db_contest

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{contest_id}/reprocess", response_model=contest_schemas.Contest, summary="Reprocess a failed contest")
def reprocess_contest(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user: user_schemas.User = Depends(get_current_user),
):
    contest = db.query(crud.models.PublishedContest).filter(crud.models.PublishedContest.id == contest_id).first()

    if not contest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contest not found")

    if contest.status != crud.models.ContestStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contest is not in FAILED state. Current state: {contest.status.name}",
        )

    contest.status = crud.models.ContestStatus.PENDING
    contest.error_message = None
    db.commit()
    db.refresh(contest)

    from .tasks import process_edict_task
    process_edict_task.delay(contest.id)

    return contest


@router.get("/", response_model=List[contest_schemas.Contest], summary="List all available contests")
def list_available_contests(
    db: Session = Depends(get_db),
):
    contests = db.query(crud.models.PublishedContest).filter(
        crud.models.PublishedContest.status == crud.models.ContestStatus.COMPLETED
    ).all()
    return contests
