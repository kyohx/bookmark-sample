from pydantic import BaseModel, ConfigDict

from ..libs.constraints import (
    FIELD_STRING_FAMILY,
    FIELD_STRING_JTI,
    FIELD_STRING_REASON,
    FIELD_STRING_USERNAME,
)
from ..libs.enum import AuthorityEnum
from ..services.authorize import Token


## ログインレスポンス
class ResponseForLogin(Token):
    pass


## リフレッシュトークンリクエスト
class RequestForRefreshToken(BaseModel):
    refresh_token: str
    "リフレッシュトークン"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "refresh_token": "YYYYYYYYYYYYYYY.YYYYYYYYYYYYYYYYY.YYYYYYYYYYYYYYYYYYYY",
                }
            ]
        }
    )


## リフレッシュレスポンス
class ResponseForRefreshToken(ResponseForLogin):
    pass


class RequestForBlacklistAddReason(BaseModel):
    reason: FIELD_STRING_REASON | None = None


class RequestForBlacklistAddJti(RequestForBlacklistAddReason):
    jti: FIELD_STRING_JTI


class RequestForBlacklistAddFamily(RequestForBlacklistAddReason):
    user: FIELD_STRING_USERNAME
    family: FIELD_STRING_FAMILY


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
