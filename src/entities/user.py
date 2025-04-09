from pydantic import BaseModel, field_serializer

from ..libs.enum import AuthorityEnum


class UserEntity(BaseModel):
    name: str
    hashed_password: str
    disabled: bool
    authority: AuthorityEnum

    @field_serializer("authority")
    def serialize_authority(self, value: AuthorityEnum) -> int:
        return value.value

    def to_response_dict(self) -> dict:
        return {
            "name": self.name,
            "authority": self.authority,
            "disabled": self.disabled,
        }
