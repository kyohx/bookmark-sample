from __future__ import annotations

from pydantic import BaseModel


#### 削除レスポンス
class ResponseForDeleteBookmark(BaseModel):
    @classmethod
    def empty(cls) -> ResponseForDeleteBookmark:
        return cls()
