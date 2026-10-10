from typing import Self

from pydantic import BaseModel, ConfigDict

from ...entities.user import UserEntity
from ...libs.enum import AuthorityEnum
from .get import UserDetail


#### 取得レスポンス
class ResponseForGetUserList(BaseModel):
    users: list[UserDetail]
    "ユーザー情報リスト"

    @classmethod
    def from_entities(cls, users: list[UserEntity]) -> Self:
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
                            "created_at": "2025-01-01T12:34:56+09:00",
                            "updated_at": "2025-01-02T09:45:01+09:00",
                        }
                    ]
                }
            ]
        }
    )
