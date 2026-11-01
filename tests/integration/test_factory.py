from sqlalchemy import select

from src.dao.models.bookmark_tag import BookmarkTagDao
from src.dao.models.tag import TagDao
from src.libs.util import get_hashed_id
from src.services.authorize import AuthorizeService

from .factory import DataFactory
from .support import TEST_HASHED_PASSWORD, SessionForTest


def test_batch_bookmarks_preserve_order_and_tag_associations(db_session: SessionForTest):
    existing = TagDao(name="existing")
    # 未flushのタグも重複作成せず再利用できる。
    db_session.add(existing)
    factory = DataFactory(db_session)

    bookmarks = factory.create_bookmarks(
        [
            ("https://example.com/first", "first", ["existing", "shared"]),
            ("https://example.com/second", "second", ["shared", "new"]),
            ("https://example.com/untagged", "untagged", []),
        ]
    )
    single = factory.create_bookmark("https://example.com/single", "single", ["shared"])

    assert [bookmark.memo for bookmark in bookmarks] == ["first", "second", "untagged"]
    assert len({bookmark.id for bookmark in [*bookmarks, single]}) == 4
    for bookmark in [*bookmarks, single]:
        assert bookmark.hashed_id == get_hashed_id(bookmark.url)
        assert bookmark.created_at is not None
        assert bookmark.updated_at is not None
    tags = {tag.name: tag.id for tag in db_session.scalars(select(TagDao))}
    assert set(tags) == {"existing", "shared", "new"}
    assert tags["existing"] == existing.id
    associations = list(
        db_session.execute(select(BookmarkTagDao.bookmark_id, BookmarkTagDao.tag_id))
    )
    assert sorted(associations) == sorted(
        [
            (bookmarks[0].id, tags["existing"]),
            (bookmarks[0].id, tags["shared"]),
            (bookmarks[1].id, tags["shared"]),
            (bookmarks[1].id, tags["new"]),
            (single.id, tags["shared"]),
        ]
    )


def test_fixed_password_hash_uses_production_settings():
    # パスワードの一致は既存のログインテストで検証し、ここではコスト等の設定差を検知する。
    assert not AuthorizeService.password_hasher.current_hasher.check_needs_rehash(
        TEST_HASHED_PASSWORD
    )
