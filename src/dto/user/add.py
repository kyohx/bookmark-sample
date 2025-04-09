from pydantic import BaseModel, ConfigDict

from ...libs.constraints import FIELD_STRING_PASSWORD, FIELD_STRING_USERNAME
from ...libs.enum import AuthorityEnum


#### 追加リクエスト
class RequestForAddUser(BaseModel):
    name: FIELD_STRING_USERNAME
    password: FIELD_STRING_PASSWORD
    authority: AuthorityEnum

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
