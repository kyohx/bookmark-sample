from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from ...libs.util import datetime_to_str

#### 取得レスポンス


# 概要
class BookmarkDigest(BaseModel):
    hashed_id: str
    url: str
    memo: str
    created_at: str
    updated_at: str

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
    bookmarks: list[BookmarkDigest]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "bookmarks": [
                        {
                            "hashed_id": "123456789012345678901234567890123456789012345678901234567890abcd",
                            "url": "https://exsample.com",
                            "memo": "サンプル",
                            "created_at": "2025-01-01 12:34:56",
                            "updated_at": "2025-01-01 12:34:56",
                        }
                    ]
                }
            ]
        }
    )
