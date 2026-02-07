from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.orm.session import Session

from ..dao.session import SessionDepend
from ..entities.user import UserEntity
from ..repositories.user import UserRepository
from .base import ServiceBase, ServiceError
from .token_blacklist import TokenBlacklistService


class Token(BaseModel):
    """
    アクセストークン
    """

    access_token: str
    "アクセストークン"
    refresh_token: str
    "リフレッシュトークン"
    token_type: str
    "トークンの種類"

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "examples": [
                {
                    "access_token": "XXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXX",
                    "refresh_token": "YYYYYYYYYYYYYYY.YYYYYYYYYYYYYYYYY.YYYYYYYYYYYYYYYYYYYY",
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


class TokenType(str, Enum):
    """
    トークン種別
    """

    ACCESS = "access"
    REFRESH = "refresh"


class AuthorizeService(ServiceBase):
    """
    認証許可サービス
    """

    ALGORITHM = "HS256"

    password_hasher = PasswordHash([BcryptHasher()])

    class Error(ServiceError):
        """
        認証許可サービスエラー
        """

        pass

    def __init__(self, session: Session) -> None:
        self.session = session
        self.jwt_secret_key = self.config.jwt_secret_key
        self.refresh_token_expire_days = self.config.refresh_token_expire_days
        self.access_token_expire_minutes = self.config.access_token_expire_minutes
        self.blacklist_service = TokenBlacklistService()

    @staticmethod
    def _get_ttl_seconds(expire_at: int) -> int:
        now = int(datetime.now(timezone.utc).timestamp())
        return max(expire_at - now, 0)

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
        return cls.password_hasher.verify(plain_password, hashed_password)

    @classmethod
    def get_hashed_password(cls, password: str) -> str:
        """
        パスワードをハッシュ化する。

        Args:
            password: ハッシュ化するパスワード

        Returns:
            ハッシュ化されたパスワード
        """
        return cls.password_hasher.hash(password)

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
        return self._create_token(
            data=data,
            expires_delta=expires_delta,
            token_type=TokenType.ACCESS,
        )

    def create_refresh_token(self, data: dict, expires_delta: timedelta) -> str:
        """
        リフレッシュトークンを作成する。

        Args:
            data: トークンに含めるデータ
            expires_delta: トークンの有効期限

        Returns:
            作成されたリフレッシュトークン
        """
        return self._create_token(
            data=data,
            expires_delta=expires_delta,
            token_type=TokenType.REFRESH,
        )

    def _create_token(self, data: dict, expires_delta: timedelta, token_type: TokenType) -> str:
        """
        トークンを作成する。

        Args:
            data: トークンに含めるデータ
            expires_delta: トークンの有効期限
            token_type: トークン種別

        Returns:
            作成されたトークン
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire, "type": token_type.value})
        encoded_jwt = jwt.encode(to_encode, self.jwt_secret_key, algorithm=self.ALGORITHM)
        return encoded_jwt

    def _decode_token(self, token: str, expected_type: TokenType) -> dict:
        """
        トークンをデコードする。

        Args:
            token: デコード対象のトークン
            expected_type: 期待するトークン種別

        Returns:
            デコード済みのペイロード

        Raises:
            AuthorizeService.Error: トークン内容が無効または期限切れ
        """
        try:
            payload = jwt.decode(token, self.jwt_secret_key, algorithms=[self.ALGORITHM])
            if payload.get("type") != expected_type.value:
                raise self.Error("Invalid token type")
            return payload
        except InvalidTokenError:
            raise self.Error("Could not validate credentials")

    def login(self, form_data: OAuth2PasswordRequestForm) -> Token:
        """
        ログイン処理を行い、アクセストークンを取得する。

        Args:
            form_data: ログインリクエストフォームデータ

        Returns:
            作成されたアクセストークン
        """
        user = self.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise self.Error("Incorrect username or password")
        if user.disabled:
            raise self.Error("Inactive user")
        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        refresh_token_expires = timedelta(days=self.refresh_token_expire_days)
        family = uuid4().hex
        refresh_jti = uuid4().hex
        access_token = self.create_access_token(
            data={"sub": user.name}, expires_delta=access_token_expires
        )
        refresh_token = self.create_refresh_token(
            data={"sub": user.name, "jti": refresh_jti, "fam": family},
            expires_delta=refresh_token_expires,
        )
        self.blacklist_service.set_current_jti(
            user.name,
            family,
            refresh_jti,
            int(refresh_token_expires.total_seconds()),
        )
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )  # nosec

    def refresh(self, refresh_token: str) -> Token:
        """
        リフレッシュトークンを使用してアクセストークンを更新する。

        Args:
            refresh_token: リフレッシュトークン

        Returns:
            新しいアクセストークンとリフレッシュトークン
        """
        payload = self._decode_token(refresh_token, expected_type=TokenType.REFRESH)
        username = payload.get("sub")
        refresh_jti = payload.get("jti")
        family = payload.get("fam")
        exp = payload.get("exp")
        if not username or not refresh_jti or not family or not exp:
            raise self.Error("Could not validate credentials")

        if self.blacklist_service.is_jti_denied(refresh_jti):
            raise self.Error("Could not validate credentials")

        if self.blacklist_service.is_family_denied(username, family):
            raise self.Error("Could not validate credentials")

        current_jti = self.blacklist_service.get_current_jti(username, family)
        if current_jti and current_jti != refresh_jti:
            ttl_seconds = self._get_ttl_seconds(exp)
            self.blacklist_service.deny_family(
                username, family, ttl_seconds, reason="reuse detected"
            )
            self.blacklist_service.deny_jti(refresh_jti, ttl_seconds, reason="reuse detected")
            raise self.Error("Could not validate credentials")
        user = self.get_user(name=username)
        if user.disabled:
            raise self.Error("Inactive user")

        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        refresh_token_expires = timedelta(days=self.refresh_token_expire_days)
        new_refresh_jti = uuid4().hex
        new_access_token = self.create_access_token(
            data={"sub": user.name}, expires_delta=access_token_expires
        )
        new_refresh_token = self.create_refresh_token(
            data={"sub": user.name, "jti": new_refresh_jti, "fam": family},
            expires_delta=refresh_token_expires,
        )
        ttl_seconds_old = self._get_ttl_seconds(exp)
        ttl_seconds_new = int(refresh_token_expires.total_seconds())
        self.blacklist_service.deny_jti(refresh_jti, ttl_seconds_old, reason="rotated")
        self.blacklist_service.set_current_jti(user.name, family, new_refresh_jti, ttl_seconds_new)
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )  # nosec

    def get_current_user_from_token(self, token: str) -> UserEntity:
        """
        トークンをデコードしてユーザーを取得する。

        Args:
            token: デコード対象のトークン

        Returns:
            トークンに対応するユーザーエンティティ

        Raises:
            AuthorizeService.Error: トークン内容が無効または期限切れ
        """
        try:
            payload = self._decode_token(token, expected_type=TokenType.ACCESS)
            username = payload.get("sub")
            if not username:
                raise self.Error("Could not validate credentials")
            token_data = TokenData(username=username)
            user = self.get_user(name=token_data.username)
        except (ValidationError, UserRepository.NotFoundError, self.Error):
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
        AuthorizeService.Error: ユーザーが無効
    """
    # サーバ側からユーザログインを即時制御するためにdisabledフラグをチェックする
    if current_user.disabled:
        raise AuthorizeService.Error("Inactive user")
    return current_user


# 依存定義
UserDepends = Annotated[UserEntity, Depends(get_current_active_user)]
