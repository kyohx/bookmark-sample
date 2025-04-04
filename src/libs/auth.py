import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..dao.operators.user import UserDaoOperator
from ..dao.session import SessionDepend
from ..entities.user import User

_DEFAULT_VALUE = "28b9ecba33eb6059e3048532bf90d7bf6484ea8a3626ac2ad2fdbdc850dc89c1"
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _DEFAULT_VALUE)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    """
    アクセストークン
    """

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    トークンデータ
    """

    username: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    パスワードを検証する
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_hashed_password(password: str) -> str:
    """
    パスワードをハッシュ化する
    """
    return pwd_context.hash(password)


def get_user(session: Session, name: str) -> User | None:
    """
    ユーザを取得する
    """
    user_dao = UserDaoOperator(session).find_one_by_name(name)
    return User(**user_dao.to_dict()) if user_dao else None


def authenticate_user(session: Session, name: str, password: str) -> User | None:
    """
    ユーザ認証処理
    """
    user = get_user(session, name)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    アクセストークンを作成する
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def login_for_access_token(form_data: OAuth2PasswordRequestForm, session: Session) -> Token:
    """
    ログイン処理からアクセストークンを取得する
    """
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.name}, expires_delta=access_token_expires)
    return Token(access_token=access_token, token_type="bearer")  # nosec


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDepend) -> User:
    """
    トークンからユーザを取得する
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(session, name=token_data.username)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    現在ログイン中かつ有効なユーザを取得する
    """
    # サーバ側からユーザログインを即時制御するためにdisabledフラグをチェックする
    if current_user.disabled:
        raise HTTPException(status_code=401, detail="Inactive user")
    return current_user


UserDepends = Annotated[User, Depends(get_current_active_user)]
