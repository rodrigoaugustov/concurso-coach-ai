from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.settings import settings
from app.users import auth, crud, schemas

router = APIRouter()

# NOVO: Endpoint de Login (Token)
@router.post("/token", summary="Get access token")
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)
):
    # 1. Busca o usuário pelo e-mail (username no form) e verifica a senha
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Cria o token JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # 3. Retorna o token
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, summary="Create a new user")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    return crud.create_user(db=db, user=user)


# NOVO: Endpoint Protegido
@router.get("/me", response_model=schemas.User, summary="Get current user's data")
def read_users_me(
    current_user: Annotated[schemas.User, Depends(auth.get_current_user)]
):
    """
    Retorna as informações do usuário logado. A mágica acontece na dependência 'get_current_user'.
    Se o token for inválido, o usuário nunca chegará a esta função.
    """
    return current_user