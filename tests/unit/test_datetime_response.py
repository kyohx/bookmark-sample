from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

import src.libs.util as util
from src.dto.bookmark.get_list import Bookmark
from src.dto.user.get import UserDetail
from src.dto.user.sessions import SessionDetail
from src.entities.bookmark import BookmarkEntity
from src.entities.session import RefreshSession
from src.entities.user import UserEntity
from src.libs.constraints import FIELD_STRING_DATETIME
from src.libs.enum import AuthorityEnum


@pytest.mark.parametrize(
    ("db_timezone", "expected"),
    [
        ("Asia/Tokyo", "2025-01-01T00:00:01+09:00"),
        ("UTC", "2025-01-01T00:00:01+00:00"),
    ],
)
def test_naive_datetime_uses_database_timezone(monkeypatch, db_timezone, expected):
    config = util.get_config().model_copy(update={"database_timezone": db_timezone})
    monkeypatch.setattr(util, "get_config", lambda: config)

    assert util.datetime_to_str(datetime(2025, 1, 1, 0, 0, 1, 999999)) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2025, 1, 1, 12, 34, 56, 999999, UTC), "2025-01-01T12:34:56+00:00"),
        (
            datetime(2025, 1, 1, 12, 34, 56, tzinfo=timezone(timedelta(hours=5, minutes=30))),
            "2025-01-01T12:34:56+05:30",
        ),
        (
            datetime(2025, 1, 1, 12, 34, 56, tzinfo=timezone(timedelta(hours=-5))),
            "2025-01-01T12:34:56-05:00",
        ),
    ],
)
def test_aware_datetime_preserves_offset_and_truncates_subseconds(value, expected):
    assert util.datetime_to_str(value) == expected
    parsed = util.str_to_datetime(expected)
    assert parsed.utcoffset() == value.utcoffset()
    assert parsed.astimezone(UTC) == value.replace(microsecond=0).astimezone(UTC)


@pytest.mark.parametrize(
    "value",
    ["2025-01-01 12:34:56", "2025-01-01T12:34:56", "2025-01-01T12:34:56.123+09:00"],
)
def test_datetime_field_rejects_legacy_naive_and_fractional_strings(value):
    with pytest.raises(ValidationError):
        TypeAdapter(FIELD_STRING_DATETIME).validate_python(value)


def test_response_details_serialize_all_datetime_fields(monkeypatch):
    config = util.get_config().model_copy(update={"database_timezone": "Asia/Tokyo"})
    monkeypatch.setattr(util, "get_config", lambda: config)
    created = datetime(2025, 1, 1, 12, 34, 56, 123456)
    updated = datetime(2025, 1, 2, 9, 45, 1, 999999, UTC)
    bookmark = Bookmark.from_entity(
        BookmarkEntity(
            hashed_id="a" * 64,
            url="https://example.com",
            memo="test",
            tags=["test"],
            created_at=created,
            updated_at=updated,
        )
    ).model_dump(mode="json")
    user = UserDetail.from_entity(
        UserEntity(
            name="test_user",
            hashed_password="unused",
            disabled=False,
            authority=AuthorityEnum.READWRITE,
            created_at=created,
            updated_at=updated,
        )
    ).model_dump(mode="json")
    for detail in (bookmark, user):
        assert detail["created_at"] == "2025-01-01T12:34:56+09:00"
        assert detail["updated_at"] == "2025-01-02T09:45:01+00:00"

    session = SessionDetail.from_entity(
        RefreshSession(
            id="session",
            created_at=created.replace(tzinfo=UTC),
            last_used_at=updated,
            expires_at=datetime(2025, 1, 3, 10, 0, 0, 123456, UTC),
            revoked=False,
            user_agent=None,
        )
    ).model_dump(mode="json")
    assert session["created_at"] == "2025-01-01T12:34:56+00:00"
    assert session["last_used_at"] == "2025-01-02T09:45:01+00:00"
    assert session["expires_at"] == "2025-01-03T10:00:00+00:00"
