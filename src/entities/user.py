from datetime import datetime

from pydantic import BaseModel, field_serializer

from ..libs.enum import AuthorityEnum


class UserEntity(BaseModel):
    name: str
    "ユーザー名"
    hashed_password: str
    "ハッシュ化されたパスワード"
    disabled: bool
    "無効フラグ"
    authority: AuthorityEnum
    "権限レベル"
    created_at: datetime | None = None
    "作成日時"
    updated_at: datetime | None = None
    "更新日時"

    @field_serializer("authority")
    def serialize_authority(self, value: AuthorityEnum) -> int:
        return value.value
