from pydantic import BaseModel, ConfigDict

from ...libs.enum import AuthorityEnum
from .get import UserDetail


#### 取得レスポンス
class ResponseForGetUserList(BaseModel):
    users: list[UserDetail]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "users": [
                        {
                            "name": "test_user",
                            "authority": AuthorityEnum.READWRITE,
                            "disabled": False,
                        }
                    ]
                }
            ]
        }
    )
