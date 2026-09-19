from typing import Self

from pydantic import BaseModel, ConfigDict

from ...entities.user import UserEntity
from ...libs.constraints import FIELD_STRING_USERNAME
from ...libs.enum import AuthorityEnum


class UserDetail(BaseModel):
    name: FIELD_STRING_USERNAME
    "ユーザー名"
    authority: AuthorityEnum
    "権限レベル"
    disabled: bool
    "無効フラグ"

    @classmethod
    def from_entity(cls, user: UserEntity) -> Self:
        return cls(
            name=user.name,
            authority=user.authority,
            disabled=user.disabled,
        )


#### 取得レスポンス
class ResponseForGetUser(BaseModel):
    user: UserDetail

    @classmethod
    def from_entity(cls, user: UserEntity) -> Self:
        return cls(user=UserDetail.from_entity(user))

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
