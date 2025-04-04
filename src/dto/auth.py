from pydantic import BaseModel

from ..libs.auth import Token


## ログインレスポンス
class ResponseForLogin(Token):
    pass


## 現在のユーザレスポンス
class ResponseForGetCurrentUser(BaseModel):
    name: str
