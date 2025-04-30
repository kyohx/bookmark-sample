from pydantic import BaseModel, ConfigDict

from ...libs.constraints import FIELD_STRING_PASSWORD, FIELD_STRING_USERNAME
from ...libs.enum import AuthorityEnum
from .get import UserDetail


#### 更新リクエスト
class RequestForUpdateUser(BaseModel):
    name: FIELD_STRING_USERNAME | None = None
    "ユーザー名"
    password: FIELD_STRING_PASSWORD | None = None
    "パスワード"
    authority: AuthorityEnum | None = None
    "権限レベル"
    disabled: bool | None = None
    "無効化フラグ"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "test_user",
                    "password": "password",
                    "authority": AuthorityEnum.READWRITE,
                    "disabled": False,
                }
            ]
        }
    )


#### 更新レスポンス
class ResponseForUpdateUser(BaseModel):
    updated_user: UserDetail

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "updated_user": {
                        "name": "test_user",
                        "authority": AuthorityEnum.READWRITE,
                        "disabled": False,
                    }
                }
            ]
        }
    )
