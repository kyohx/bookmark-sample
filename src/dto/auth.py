from pydantic import BaseModel

from ..libs.enum import AuthorityEnum
from ..services.auth import Token


## ログインレスポンス
class ResponseForLogin(Token):
    pass


## 現在のユーザレスポンス
class ResponseForGetCurrentUser(BaseModel):
    name: str
    authority: AuthorityEnum
