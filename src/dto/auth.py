from pydantic import BaseModel, ConfigDict

from ..libs.constraints import FIELD_STRING_USERNAME
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
