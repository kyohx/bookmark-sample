from pydantic import BaseModel, ConfigDict

from ..libs.constraints import (
    FIELD_STRING_PASSWORD,
    FIELD_STRING_REFRESH_TOKEN,
    FIELD_STRING_USERNAME,
)
from ..libs.enum import AuthorityEnum


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
                    "access_token": "XXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXX",  # nosec
                    "refresh_token": "YYYYYYYYYYYYYYY.YYYYYYYYYYYYYYYYY.YYYYYYYYYYYYYYYYYYYY",  # nosec
                    "token_type": "bearer",
                }
            ]
        },
    )


## ログイン入力バリデーション
class RequestForLogin(BaseModel):
    username: FIELD_STRING_USERNAME
    "ユーザー名"
    password: FIELD_STRING_PASSWORD
    "パスワード"


## ログインレスポンス
class ResponseForLogin(Token):
    pass


## リフレッシュトークンリクエスト
class RequestForRefreshToken(BaseModel):
    refresh_token: FIELD_STRING_REFRESH_TOKEN
    "リフレッシュトークン"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "refresh_token": "YYYYYYYYYYYYYYY.YYYYYYYYYYYYYYYYY.YYYYYYYYYYYYYYYYYYYY",  # nosec
                }
            ]
        }
    )


## リフレッシュレスポンス
class ResponseForRefreshToken(ResponseForLogin):
    pass


## 現在のユーザレスポンス
class ResponseForGetCurrentUser(BaseModel):
    name: FIELD_STRING_USERNAME
    "ユーザー名"
    authority: AuthorityEnum
    "権限レベル"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "test_user",
                    "authority": AuthorityEnum.READWRITE,
                }
            ]
        }
    )
