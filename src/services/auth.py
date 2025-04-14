from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, ValidationError

from ..dao.session import SessionDepend
from ..entities.user import UserEntity
from ..repositories.user import UserRepository
from .base import ServiceBase


class Token(BaseModel):
    """
    アクセストークン
    """

    access_token: str
    token_type: str

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "examples": [
                {
                    "access_token": "XXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXX",
                    "token_type": "bearer",
                }
            ]
        }
    )
 


class TokenData(BaseModel):
    """
    トークンデータ
    """

    username: str

    model_config = ConfigDict(frozen=True)


class AuthorizeService(ServiceBase):
    """
    認証許可サービス
    """

    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 20

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.jwt_secret_key = self.config.jwt_secret_key

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """
        パスワードを検証する
        """
        return cls.pwd_context.verify(plain_password, hashed_password)

    @classmethod
    def get_hashed_password(cls, password: str) -> str:
        """
        パスワードをハッシュ化する
        """
        return cls.pwd_context.hash(password)

    def get_user(self, name: str) -> UserEntity:
        """
        ユーザを取得する
        """
        return UserRepository(self.session).find_one(name)

    def authenticate_user(self, name: str, password: str) -> UserEntity | None:
        """
        ユーザ認証処理
        """
        try:
            user = self.get_user(name)
        except UserRepository.NotFoundError:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(self, data: dict, expires_delta: timedelta) -> str:
        """
        アクセストークンを作成する
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.jwt_secret_key, algorithm=self.ALGORITHM)
        return encoded_jwt

    def get_exception(self, detail: str) -> HTTPException:
        """
        認証エラーを作成する
        """
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    def login(self, form_data: OAuth2PasswordRequestForm) -> Token:
        """
        ログイン処理からアクセストークンを取得する
        """
        user = self.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise self.get_exception(detail="Incorrect username or password")
        access_token_expires = timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": user.name}, expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")  # nosec

    def get_current_user_from_token(self, token: str) -> UserEntity:
        """
        トークンからユーザを取得する
        """
        try:
            payload = jwt.decode(token, self.jwt_secret_key, algorithms=[self.ALGORITHM])
            token_data = TokenData(username=payload.get("sub"))
            user = self.get_user(name=token_data.username)
        except (InvalidTokenError, ValidationError, UserRepository.NotFoundError):
            raise self.get_exception(detail="Could not validate credentials")
        return user


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user_from_token(
    token: Annotated[str, Depends(oauth2_scheme)], session: SessionDepend
) -> UserEntity:
    """
    トークンからユーザを取得する
    """
    return AuthorizeService(session=session).get_current_user_from_token(token=token)


def get_current_active_user(
    current_user: Annotated[UserEntity, Depends(get_current_user_from_token)],
):
    """
    現在ログイン中かつ有効なユーザを取得する
    """
    # サーバ側からユーザログインを即時制御するためにdisabledフラグをチェックする
    if current_user.disabled:
        raise HTTPException(status_code=401, detail="Inactive user")
    return current_user


# 依存定義
UserDepends = Annotated[UserEntity, Depends(get_current_active_user)]
