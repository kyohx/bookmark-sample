from typing import Self

from pydantic import BaseModel, ConfigDict, field_serializer

from ...entities.bookmark import BookmarkEntity
from ...libs.constraints import FIELD_STRING_MAX400, FIELD_TAGS, FIELD_URL
from .get_list import Bookmark


#### 追加リクエスト
class RequestForAddBookmark(BaseModel):
    url: FIELD_URL
    "URL"
    memo: FIELD_STRING_MAX400
    "メモ"
    tags: FIELD_TAGS
    "タグ"

    @field_serializer("url")
    def serialize_url(self, value) -> str:
        return str(value)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "url": "https://example.com",
                    "memo": "サンプル",
                    "tags": [
                        "work",
                        "test",
                    ],
                }
            ]
        }
    )


#### 追加レスポンス
class ResponseForAddBookmark(BaseModel):
    added_bookmark: Bookmark
    "追加後のブックマーク情報"

    @classmethod
    def from_entity(cls, bookmark: BookmarkEntity) -> Self:
        return cls(added_bookmark=Bookmark.from_entity(bookmark))

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "added_bookmark": {
                        "hashed_id": "123456789012345678901234567890123456789012345678901234567890abcd",
                        "url": "https://example.com",
                        "memo": "サンプル",
                        "tags": [
                            "work",
                            "test",
                        ],
                        "created_at": "2025-01-01 12:34:56",
                        "updated_at": "2025-01-01 12:34:56",
                    },
                }
            ]
        }
    )
