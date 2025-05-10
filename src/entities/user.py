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

    @field_serializer("authority")
    def serialize_authority(self, value: AuthorityEnum) -> int:
        return value.value

    def to_response_dict(self) -> dict:
        """
        ユーザー情報をレスポンス用の辞書に変換する。

        Returns:
            レスポンス用の辞書
        """
        return {
            "name": self.name,
            "authority": self.authority,
            "disabled": self.disabled,
        }
