from pydantic import BaseModel, ConfigDict, field_serializer

from ...libs.constraints import FIELD_HASHED_ID, FIELD_STRING_MAX400, FIELD_TAGS, FIELD_URL


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
                    "url": "https://exsample.com",
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
    hashed_id: FIELD_HASHED_ID
    "URLハッシュID"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "hashed_id": "123456789012345678901234567890123456789012345678901234567890abcd",
                }
            ]
        }
    )
