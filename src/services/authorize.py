from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.orm.session import Session

from ..dao.session import SessionDepend
from ..entities.user import UserEntity
from ..repositories.user import UserRepository
from .base import ServiceBase, ServiceError


class Token(BaseModel):
    """
    アクセストークン
    """

    access_token: str
    "アクセストークン"
    token_type: str
    "トークンの種類"

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "examples": [
                {
                    "access_token": "XXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXX",
                    "token_type": "bearer",
                }
            ]
        },
    )


class TokenData(BaseModel):
    """
    トークンデータ
    """

    username: str
    "ユーザー名"

    model_config = ConfigDict(frozen=True)


class AuthorizeService(ServiceBase):
    """
    認証許可サービス
    """

    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 20

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    class Error(ServiceError):
        """
        認証許可サービスエラー
        """

        pass

    def __init__(self, session: Session) -> None:
        self.session = session
        self.jwt_secret_key = self.config.jwt_secret_key

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """
        パスワードを検証する。

        Args:
            plain_password: 平文のパスワード
            hashed_password: ハッシュ化されたパスワード

        Returns:
            パスワードが一致する場合はTrue、それ以外はFalse
        """
        return cls.pwd_context.verify(plain_password, hashed_password)

    @classmethod
    def get_hashed_password(cls, password: str) -> str:
        """
        パスワードをハッシュ化する。

        Args:
            password: ハッシュ化するパスワード

        Returns:
            ハッシュ化されたパスワード
        """
        return cls.pwd_context.hash(password)

    def get_user(self, name: str) -> UserEntity:
        """
        ユーザー名を指定してユーザーを取得する。

        Args:
            name: 検索対象のユーザー名

        Returns:
            取得したユーザーエンティティ
        """
        return UserRepository(self.session).find_one(name)

    def authenticate_user(self, name: str, password: str) -> UserEntity | None:
        """
        ユーザー名とパスワードを使用してユーザーを認証する

        Args:
            name: ユーザー名
            password: パスワード

        Returns:
            認証に成功したユーザーエンティティ、認証に失敗した場合はNone
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
        アクセストークンを作成する。

        Args:
            data: トークンに含めるデータ
            expires_delta: トークンの有効期限

        Returns:
            作成されたアクセストークン
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.jwt_secret_key, algorithm=self.ALGORITHM)
        return encoded_jwt

    def login(self, form_data: OAuth2PasswordRequestForm) -> Token:
        """
        ログイン処理を行い、アクセストークンを取得する。

        Args:
            form_data: ログインリクエストフォームデータ

        Returns:
            Token: 作成されたアクセストークン
        """
        user = self.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise self.Error("Incorrect username or password")
        access_token_expires = timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": user.name}, expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")  # nosec

    def get_current_user_from_token(self, token: str) -> UserEntity:
        """
        トークンをデコードしてユーザーを取得する。

        Args:
            token: デコード対象のトークン

        Returns:
            トークンに対応するユーザーエンティティ

        Raises:
            HTTPException: トークン内容が無効または期限切れ
        """
        try:
            payload = jwt.decode(token, self.jwt_secret_key, algorithms=[self.ALGORITHM])
            token_data = TokenData(username=payload.get("sub"))
            user = self.get_user(name=token_data.username)
        except (InvalidTokenError, ValidationError, UserRepository.NotFoundError):
            raise self.Error("Could not validate credentials")
        return user


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user_from_token(
    token: Annotated[str, Depends(oauth2_scheme)], session: SessionDepend
) -> UserEntity:
    """
    トークンを使用して現在のユーザーを取得する。

    Args:
        token: リクエストヘッダーから取得したトークン
        session: データベースセッション

    Returns:
        トークンに対応するユーザーエンティティ
    """
    return AuthorizeService(session=session).get_current_user_from_token(token=token)


def get_current_active_user(
    current_user: Annotated[UserEntity, Depends(get_current_user_from_token)],
) -> UserEntity:
    """
    現在ログイン中かつ有効なユーザーを取得する。

    Args:
        current_user: 現在のユーザーエンティティ

    Returns:
        有効なユーザーエンティティ

    Raises:
        HTTPException: ユーザーが無効
    """
    # サーバ側からユーザログインを即時制御するためにdisabledフラグをチェックする
    if current_user.disabled:
        raise AuthorizeService.Error("Inactive user")
    return current_user


# 依存定義
UserDepends = Annotated[UserEntity, Depends(get_current_active_user)]
