from pydantic import BaseModel, ConfigDict

from ..libs.enum import AuthorityEnum
from ..services.auth import Token
from ..libs.constraints import FIELD_STRING_USERNAME


## ログインレスポンス
class ResponseForLogin(Token):
    pass


## 現在のユーザレスポンス
class ResponseForGetCurrentUser(BaseModel):
    name: FIELD_STRING_USERNAME
    authority: AuthorityEnum

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
