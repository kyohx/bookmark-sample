from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from ...libs.constraints import (
    FIELD_HASHED_ID,
    FIELD_STRING_DATETIME,
    FIELD_STRING_MAX400,
    FIELD_TAGS,
    FIELD_URL,
)
from ...libs.util import datetime_to_str

#### 取得レスポンス


# ブックマーク情報
class Bookmark(BaseModel):
    hashed_id: FIELD_HASHED_ID
    "URLハッシュID"
    url: FIELD_URL
    "URL"
    memo: FIELD_STRING_MAX400
    "メモ"
    created_at: FIELD_STRING_DATETIME
    "作成日時"
    updated_at: FIELD_STRING_DATETIME
    "更新日時"
    tags: FIELD_TAGS
    "タグ"

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return datetime_to_str(value)
        raise ValueError("Invalid type")

    @field_validator("updated_at", mode="before")
    @classmethod
    def parse_updated_at(cls, value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return datetime_to_str(value)
        raise ValueError("Invalid type")


#### リスト取得レスポンス
class ResponseForGetBookmarkList(BaseModel):
    bookmarks: list[Bookmark]
    "ブックマーク情報リスト"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "bookmarks": [
                        {
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
                    ]
                }
            ]
        }
    )
