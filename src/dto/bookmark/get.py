from typing import Self

from pydantic import BaseModel, ConfigDict

from ...entities.bookmark import BookmarkEntity
from .get_list import Bookmark


#### 詳細取得レスポンス
class ResponseForGetBookmark(BaseModel):
    bookmark: Bookmark
    "ブックマーク情報"

    @classmethod
    def from_entity(cls, bookmark: BookmarkEntity) -> Self:
        return cls(bookmark=Bookmark.from_entity(bookmark))

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "bookmark": {
                        "hashed_id": "123456789012345678901234567890123456789012345678901234567890abcd",
                        "url": "https://example.com",
                        "memo": "サンプル",
                        "tags": [
                            "private",
                            "test",
                        ],
                        "created_at": "2025-01-01T12:34:56+09:00",
                        "updated_at": "2025-01-02T09:45:01+09:00",
                    }
                }
            ]
        }
    )
