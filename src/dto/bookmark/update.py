from pydantic import BaseModel, ConfigDict

from ...libs.constraints import FIELD_STRING_MAX400, FIELD_TAGS
from .get import BookmarkDetail


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
    updated_bookmark: BookmarkDetail
    "更新後のブックマーク情報"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "updated_bookmark": {
                        "hashed_id": "123456789012345678901234567890123456789012345678901234567890abcd",
                        "url": "https://exsample.com",
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
