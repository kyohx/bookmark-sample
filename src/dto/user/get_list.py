from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ...entities.user import UserEntity
from ...libs.enum import AuthorityEnum
from .get import UserDetail


#### 取得レスポンス
class ResponseForGetUserList(BaseModel):
    users: list[UserDetail]
    "ユーザー情報リスト"

    @classmethod
    def from_entities(cls, users: list[UserEntity]) -> ResponseForGetUserList:
        return cls(users=[UserDetail.from_entity(user) for user in users])

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
