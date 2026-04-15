"""
Autenticação JWT para o ContaFácil SaaS.
Cada contador é um tenant isolado — só acessa os próprios relatórios.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import Contador

# ── Configurações ─────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "contafacil-secret-key-mude-em-producao-2024")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_HOURS = 72  # 3 dias

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Senha ─────────────────────────────────────────────────────────────────────

def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, hashed: str) -> bool:
    return bcrypt.checkpw(senha.encode(), hashed.encode())


# ── Token JWT ─────────────────────────────────────────────────────────────────

def criar_token(contador_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(contador_id), "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Contador:
    """Dependência FastAPI — valida o token e retorna o contador logado."""
    credencial_err = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        contador_id: Optional[str] = payload.get("sub")
        if contador_id is None:
            raise credencial_err
    except JWTError:
        raise credencial_err

    contador = db.query(Contador).filter(Contador.id == int(contador_id)).first()
    if contador is None:
        raise credencial_err
    return contador
