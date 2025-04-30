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
    "URLハッシュID"
    url: FIELD_URL
    "URL"
    memo: FIELD_STRING_MAX400
    "メモ"
    created_at: datetime | None = None
    "作成日時"
    updated_at: datetime | None = None
    "更新日時"
    tags: FIELD_TAGS | None = None
    "タグ"

    @field_serializer("url")
    def serialize_url(self, value) -> str:
        return str(value)
