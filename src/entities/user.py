from pydantic import BaseModel

from ..libs.enum import AuthorityEnum


class User(BaseModel):
    name: str
    hashed_password: str
    disabled: bool = False
    authority: AuthorityEnum
