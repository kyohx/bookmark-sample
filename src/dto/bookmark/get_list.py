from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator

from ...entities.bookmark import BookmarkEntity
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
        """
        作成日時をレスポンス用の文字列に変換する。

        Args:
            value: 文字列または datetime の作成日時

        Returns:
            入力文字列またはタイムゾーン付き・秒精度の ISO 8601 形式の文字列

        Raises:
            ValueError: 入力が文字列でも datetime でもない場合
        """
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return datetime_to_str(value)
        raise ValueError("Invalid type")

    @field_validator("updated_at", mode="before")
    @classmethod
    def parse_updated_at(cls, value) -> str:
        """
        更新日時をレスポンス用の文字列に変換する。

        Args:
            value: 文字列または datetime の更新日時

        Returns:
            入力文字列またはタイムゾーン付き・秒精度の ISO 8601 形式の文字列

        Raises:
            ValueError: 入力が文字列でも datetime でもない場合
        """
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return datetime_to_str(value)
        raise ValueError("Invalid type")

    @classmethod
    def from_entity(cls, bookmark: BookmarkEntity) -> Self:
        """ブックマークエンティティを検証してレスポンス用のブックマーク情報を生成する。"""
        return cls.model_validate(bookmark.model_dump(exclude_none=True))


#### リスト取得レスポンス
class ResponseForGetBookmarkList(BaseModel):
    bookmarks: list[Bookmark]
    "ブックマーク情報リスト"

    @classmethod
    def from_entities(cls, bookmarks: list[BookmarkEntity]) -> Self:
        """ブックマークエンティティを入力順に変換して一覧レスポンスを生成する。"""
        return cls(bookmarks=[Bookmark.from_entity(bookmark) for bookmark in bookmarks])

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
                            "created_at": "2025-01-01T12:34:56+09:00",
                            "updated_at": "2025-01-02T09:45:01+09:00",
                        }
                    ]
                }
            ]
        }
    )
