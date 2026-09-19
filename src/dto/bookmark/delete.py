from typing import Self

from pydantic import BaseModel


#### 削除レスポンス
class ResponseForDeleteBookmark(BaseModel):
    @classmethod
    def empty(cls) -> Self:
        return cls()
