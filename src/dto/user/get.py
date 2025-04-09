from pydantic import BaseModel, ConfigDict

from ...libs.enum import AuthorityEnum


class UserDetail(BaseModel):
    name: str
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
