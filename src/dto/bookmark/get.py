from pydantic import BaseModel, ConfigDict

from ...libs.constraints import FIELD_TAGS
from .get_list import BookmarkDigest


# 詳細
class BookmarkDetail(BookmarkDigest):
    tags: FIELD_TAGS


#### 詳細取得レスポンス
class ResponseForGetBookmark(BaseModel):
    bookmark: BookmarkDetail

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "bookmark": {
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
