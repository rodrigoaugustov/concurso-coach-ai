from pydantic import BaseModel, EmailStr

# Schema base com os campos comuns
class UserBase(BaseModel):
    name: str
    email: EmailStr

# Schema para a criação de um usuário (recebe a senha)
class UserCreate(UserBase):
    password: str

# Schema para a leitura de um usuário (não expõe a senha)
# Este schema será usado nas respostas da API.
class User(UserBase):
    id: int

    # Configuração para permitir que o Pydantic leia dados de modelos ORM (SQLAlchemy)
    class Config:
        from_attributes = True