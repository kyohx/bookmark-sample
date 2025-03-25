from datetime import datetime

from pydantic import BaseModel, field_serializer

from ..libs.constraints import FIELD_HASHED_ID, FIELD_STRING_MAX400, FIELD_TAGS, FIELD_URL

# エンティティ
# ユースケース層で使用されるデータ


class BookmarkEntity(BaseModel):
    """
    ブックマーク
    """

    hashed_id: FIELD_HASHED_ID | None = None
    url: FIELD_URL
    memo: FIELD_STRING_MAX400
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tags: FIELD_TAGS | None = None

    @field_serializer("url")
    def serialize_url(self, value) -> str:
        return str(value)
