from pydantic import BaseModel, ConfigDict, field_serializer

from ...libs.constraints import FIELD_STRING_MAX400, FIELD_TAGS, FIELD_URL


#### 追加リクエスト
class RequestForAddBookmark(BaseModel):
    url: FIELD_URL
    memo: FIELD_STRING_MAX400
    tags: FIELD_TAGS

    @field_serializer("url")
    def serialize_url(self, value):
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
    hashed_id: str
