from pydantic import BaseModel

from ..libs.auth import Token
from ..libs.enum import AuthorityEnum


## ログインレスポンス
class ResponseForLogin(Token):
    pass


## 現在のユーザレスポンス
class ResponseForGetCurrentUser(BaseModel):
    name: str
    authority: AuthorityEnum
