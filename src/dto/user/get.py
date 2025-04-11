from pydantic import BaseModel, ConfigDict

from ...libs.constraints import FIELD_STRING_USERNAME
from ...libs.enum import AuthorityEnum


class UserDetail(BaseModel):
    name: FIELD_STRING_USERNAME
    authority: AuthorityEnum
    disabled: bool


#### 取得レスポンス
class ResponseForGetUser(BaseModel):
    user: UserDetail

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user": {
                        "name": "test_user",
                        "authority": AuthorityEnum.READWRITE,
                        "disabled": False,
                    }
                }
            ]
        }
    )
