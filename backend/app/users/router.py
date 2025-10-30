from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.settings import settings
from app.users import auth, crud, schemas
from app.core.security import InputValidator

# Rate limiting (decorator) - optional if slowapi available
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
except Exception:
    limiter = None

router = APIRouter()

limit_login = (limiter.limit("10/hour") if limiter else (lambda f: f))

@router.post("/token", summary="Get access token")
@limit_login
def login_for_access_token(
    request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db),
):
    email = (form_data.username or "").strip()
    password = form_data.password or ""

    # Validação e sanitização de credenciais
    if not InputValidator.validate_email(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")
    if not InputValidator.validate_password_strength(password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Weak password format")

    user = crud.get_user_by_email(db, email=email)
    if not user or not auth.verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, summary="Create a new user")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Sanitização básica
    if not InputValidator.validate_email(user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")
    if not InputValidator.validate_password_strength(user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Weak password format")

    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    return crud.create_user(db=db, user=user)


@router.get("/me", response_model=schemas.User, summary="Get current user's data")
def read_users_me(
    current_user: Annotated[schemas.User, Depends(auth.get_current_user)]
):
    return current_user
