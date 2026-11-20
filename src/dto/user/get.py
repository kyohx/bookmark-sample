from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator

from ...entities.user import UserEntity
from ...libs.constraints import FIELD_STRING_DATETIME, FIELD_STRING_USERNAME
from ...libs.enum import AuthorityEnum
from ...libs.util import datetime_to_str


class UserDetail(BaseModel):
    name: FIELD_STRING_USERNAME
    "ユーザー名"
    authority: AuthorityEnum
    "権限レベル"
    disabled: bool
    "無効フラグ"
    created_at: FIELD_STRING_DATETIME
    "作成日時"
    updated_at: FIELD_STRING_DATETIME
    "更新日時"

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, value) -> str:
        """
        作成日時をレスポンス用の文字列に変換する。

        Args:
            value: 文字列または datetime の作成日時

        Returns:
            入力文字列またはタイムゾーン付き・秒精度の ISO 8601 形式の文字列

        Raises:
            ValueError: 入力が文字列でも datetime でもない場合
        """
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return datetime_to_str(value)
        raise ValueError("Invalid type")

    @field_validator("updated_at", mode="before")
    @classmethod
    def parse_updated_at(cls, value) -> str:
        """
        更新日時をレスポンス用の文字列に変換する。

        Args:
            value: 文字列または datetime の更新日時

        Returns:
            入力文字列またはタイムゾーン付き・秒精度の ISO 8601 形式の文字列

        Raises:
            ValueError: 入力が文字列でも datetime でもない場合
        """
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return datetime_to_str(value)
        raise ValueError("Invalid type")

    @classmethod
    def from_entity(cls, user: UserEntity) -> Self:
        """ユーザーエンティティを検証してレスポンス用のユーザー情報を生成する。"""
        return cls.model_validate(user.model_dump(exclude_none=True))


#### 取得レスポンス
class ResponseForGetUser(BaseModel):
    user: UserDetail

    @classmethod
    def from_entity(cls, user: UserEntity) -> Self:
        """ユーザーエンティティから詳細取得レスポンスを生成する。"""
        return cls(user=UserDetail.from_entity(user))

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user": {
                        "name": "test_user",
                        "authority": AuthorityEnum.READWRITE,
                        "disabled": False,
                        "created_at": "2025-01-01T12:34:56+09:00",
                        "updated_at": "2025-01-02T09:45:01+09:00",
                    }
                }
            ]
        }
    )
