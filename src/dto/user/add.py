from pydantic import BaseModel, ConfigDict

from ...libs.constraints import FIELD_STRING_PASSWORD, FIELD_STRING_USERNAME
from ...libs.enum import AuthorityEnum


#### 追加リクエスト
class RequestForAddUser(BaseModel):
    name: FIELD_STRING_USERNAME
    "ユーザー名"
    password: FIELD_STRING_PASSWORD
    "パスワード"
    authority: AuthorityEnum
    "権限レベル"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "test_user",
                    "password": "password",
                    "authority": AuthorityEnum.READWRITE,
                }
            ]
        }
    )


#### 追加レスポンス
class ResponseForAddUser(BaseModel):
    pass
