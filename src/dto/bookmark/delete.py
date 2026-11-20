from typing import Self

from pydantic import BaseModel


#### 削除レスポンス
class ResponseForDeleteBookmark(BaseModel):
    @classmethod
    def empty(cls) -> Self:
        """本文にフィールドを持たない削除レスポンスを生成する。"""
        return cls()
