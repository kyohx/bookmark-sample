from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ...entities.bookmark import BookmarkEntity
from ...libs.constraints import FIELD_STRING_MAX400, FIELD_TAGS
from .get_list import Bookmark


#### 更新リクエスト
class RequestForUpdateBookmark(BaseModel):
    memo: FIELD_STRING_MAX400 | None = None
    "メモ"
    tags: FIELD_TAGS | None = None
    "タグ"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "memo": "サンプル",
                    "tags": [
                        "private",
                        "test",
                    ],
                }
            ]
        }
    )


#### 更新レスポンス
class ResponseForUpdateBookmark(BaseModel):
    updated_bookmark: Bookmark
    "更新後のブックマーク情報"

    @classmethod
    def from_entity(cls, bookmark: BookmarkEntity) -> ResponseForUpdateBookmark:
        return cls(updated_bookmark=Bookmark.from_entity(bookmark))

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "updated_bookmark": {
                        "hashed_id": "123456789012345678901234567890123456789012345678901234567890abcd",
                        "url": "https://example.com",
                        "memo": "サンプル",
                        "tags": [
                            "private",
                            "test",
                        ],
                        "created_at": "2025-01-01 12:34:56",
                        "updated_at": "2025-01-01 12:34:56",
                    }
                }
            ]
        }
    )
