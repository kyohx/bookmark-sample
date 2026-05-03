from collections.abc import Iterator
from threading import Barrier, Lock, Thread

import pytest
from dogpile.cache.api import NO_VALUE
from dogpile.cache.region import CacheRegion
from sqlalchemy.orm import Session

from src.dao.models.base import BaseDao
from src.dao.models.bookmark import BookmarkDao
from src.dao.models.tag import TagDao
from src.dao.models.user import UserDao
from src.entities.bookmark import BookmarkEntity
from src.entities.user import UserEntity
from src.libs.enum import AuthorityEnum
from src.libs.page import Page
from src.libs.util import get_hashed_id
from src.repositories.bookmark import BookmarkRepository
from src.repositories.user import UserRepository
from tests.unit.factory import UnitDataFactory


@pytest.fixture
def session(sqlite_session_factory) -> Iterator[Session]:
    with sqlite_session_factory(BaseDao.metadata) as db_session:
        yield db_session


class ConcurrentVersionRegion:
    """
    初回 version 取得の競合を再現する、最小限のテスト用 region。
    """

    def __init__(self, parties: int) -> None:
        self._value: object = NO_VALUE
        self._barrier = Barrier(parties)
        self._lock = Lock()

    def get(
        self, key: str, expiration_time: float | None = None, ignore_expiration: bool = False
    ) -> object:
        del key, expiration_time, ignore_expiration
        self._barrier.wait()
        return self._value

    def get_or_create(self, key: str, creator, expiration_time: float | None = None) -> object:
        del key, expiration_time
        with self._lock:
            if self._value is NO_VALUE:
                self._value = creator()
            return self._value

    def set(self, key: str, value: object, expiration_time: int | None = None) -> None:
        del key, expiration_time
        self._value = value

    def delete(self, key: str) -> None:
        del key
        self._value = NO_VALUE


def test_user_repository_find_one_cache_and_invalidation(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    ユーザー詳細キャッシュは再利用され、更新後に無効化される
    """
    UnitDataFactory(session).create_user("alice")
    repository = UserRepository(session, region=memory_region)

    calls = 0
    original = repository.user_operator.find_one_by_name

    def wrapped(name: str) -> UserDao | None:
        # 実 DB 参照回数を数え、2 回目以降が cache hit かを判定する。
        nonlocal calls
        calls += 1
        return original(name)

    monkeypatch.setattr(repository.user_operator, "find_one_by_name", wrapped)

    first = repository.find_one(name="alice")
    second = repository.find_one(name="alice")
    assert first.name == second.name == "alice"
    assert calls == 1

    first.name = "alice-renamed"
    first.disabled = True
    repository.update_one(first, current_name="alice")

    # 更新後は古い詳細キャッシュが無効化され、再度 DB を読む。
    refreshed = repository.find_one(name="alice-renamed")
    cached = repository.find_one(name="alice-renamed")
    assert refreshed.name == cached.name == "alice-renamed"
    assert refreshed.disabled is True
    assert calls == 3


def test_user_repository_find_one_not_found_is_not_cached(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    未存在ユーザーの詳細取得はキャッシュされず毎回再評価される
    """
    repository = UserRepository(session, region=memory_region)

    calls = 0
    original = repository.user_operator.find_one_by_name

    def wrapped(name: str) -> UserDao | None:
        # NotFoundError で終わるケースでも、都度 DB 参照が走ることを確認する。
        nonlocal calls
        calls += 1
        return original(name)

    monkeypatch.setattr(repository.user_operator, "find_one_by_name", wrapped)

    with pytest.raises(UserRepository.NotFoundError, match="Not found specified data."):
        repository.find_one(name="missing-user")

    with pytest.raises(UserRepository.NotFoundError, match="Not found specified data."):
        repository.find_one(name="missing-user")

    # 例外結果はキャッシュされず、毎回 DAO が呼ばれる。
    assert calls == 2


def test_user_repository_find_all_cache_is_invalidated_on_add(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    ユーザー一覧キャッシュは追加後に無効化される
    """
    UnitDataFactory(session).create_user("alice")
    repository = UserRepository(
        session,
        page=Page(number=1, size=10),
        region=memory_region,
    )

    calls = 0
    original = repository.user_operator.find_all

    def wrapped() -> list[UserDao]:
        # 一覧キャッシュの有無を DB 呼び出し回数で見る。
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(repository.user_operator, "find_all", wrapped)

    first = repository.find_all()
    second = repository.find_all()
    assert sorted(user.name for user in first) == sorted(user.name for user in second) == ["alice"]
    assert calls == 1

    repository.add_one(
        UserEntity(
            name="bob",
            hashed_password="hashed-password",
            disabled=False,
            authority=AuthorityEnum.READWRITE,
        )
    )

    # add 後は一覧 version が進み、一覧クエリが再評価される。
    refreshed = repository.find_all()
    cached = repository.find_all()
    assert sorted(user.name for user in refreshed) == ["alice", "bob"]
    assert sorted(user.name for user in cached) == ["alice", "bob"]
    assert calls == 2


def test_user_repository_find_all_cache_separates_page_number(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    ユーザー一覧キャッシュはページ番号ごとに別キーになる
    """
    UnitDataFactory(session).create_user("alice")
    UnitDataFactory(session).create_user("bob")
    first_page_repository = UserRepository(
        session,
        page=Page(number=1, size=1),
        region=memory_region,
    )
    second_page_repository = UserRepository(
        session,
        page=Page(number=2, size=1),
        region=memory_region,
    )

    first_page_calls = 0
    second_page_calls = 0
    original_first_page = first_page_repository.user_operator.find_all
    original_second_page = second_page_repository.user_operator.find_all

    def wrapped_first_page() -> list[UserDao]:
        # 同じ region を共有しても、ページ番号が違えば別クエリとして評価されることを見る。
        nonlocal first_page_calls
        first_page_calls += 1
        return original_first_page()

    def wrapped_second_page() -> list[UserDao]:
        # page=2 の取得が page=1 のキャッシュを誤 reuse しないことを見る。
        nonlocal second_page_calls
        second_page_calls += 1
        return original_second_page()

    monkeypatch.setattr(first_page_repository.user_operator, "find_all", wrapped_first_page)
    monkeypatch.setattr(second_page_repository.user_operator, "find_all", wrapped_second_page)

    first_page = first_page_repository.find_all()
    cached_first_page = first_page_repository.find_all()
    second_page = second_page_repository.find_all()
    cached_second_page = second_page_repository.find_all()

    # 各ページは最初の 1 回だけ DB に到達し、同一ページ内では cache hit する。
    assert len(first_page) == len(cached_first_page) == 1
    assert len(second_page) == len(cached_second_page) == 1
    assert first_page_calls == 1
    assert second_page_calls == 1


def test_user_repository_find_all_cache_invalidation_reaches_all_pages(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    ユーザー一覧キャッシュの無効化は別ページの一覧にも伝播する
    """
    UnitDataFactory(session).create_user("alice")
    UnitDataFactory(session).create_user("bob")
    first_page_repository = UserRepository(
        session,
        page=Page(number=1, size=1),
        region=memory_region,
    )
    second_page_repository = UserRepository(
        session,
        page=Page(number=2, size=1),
        region=memory_region,
    )

    first_page_calls = 0
    second_page_calls = 0
    original_first_page = first_page_repository.user_operator.find_all
    original_second_page = second_page_repository.user_operator.find_all

    def wrapped_first_page() -> list[UserDao]:
        # 追加前後で page=1 の一覧が再評価されるかを追跡する。
        nonlocal first_page_calls
        first_page_calls += 1
        return original_first_page()

    def wrapped_second_page() -> list[UserDao]:
        # version bump により page=2 の一覧も巻き込んで無効化されることを見る。
        nonlocal second_page_calls
        second_page_calls += 1
        return original_second_page()

    monkeypatch.setattr(first_page_repository.user_operator, "find_all", wrapped_first_page)
    monkeypatch.setattr(second_page_repository.user_operator, "find_all", wrapped_second_page)

    first_page_repository.find_all()
    first_page_repository.find_all()
    second_page_repository.find_all()
    second_page_repository.find_all()
    assert first_page_calls == 1
    assert second_page_calls == 1

    first_page_repository.add_one(
        UserEntity(
            name="charlie",
            hashed_password="hashed-password",
            disabled=False,
            authority=AuthorityEnum.READWRITE,
        )
    )

    refreshed_first_page = first_page_repository.find_all()
    cached_first_page = first_page_repository.find_all()
    refreshed_second_page = second_page_repository.find_all()
    cached_second_page = second_page_repository.find_all()

    # list namespace の version が進むと、全ページ条件で 1 回ずつ再クエリされる。
    assert len(refreshed_first_page) == len(cached_first_page) == 1
    assert len(refreshed_second_page) == len(cached_second_page) == 1
    assert first_page_calls == 2
    assert second_page_calls == 2


def test_bookmark_repository_find_one_cache_and_invalidation(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    ブックマーク詳細キャッシュは再利用され、更新後に無効化される
    """
    bookmark = UnitDataFactory(session).create_bookmark(
        "https://example.com/1",
        "before",
        ["tag1"],
    )
    repository = BookmarkRepository(session, region=memory_region)

    bookmark_calls = 0
    tag_calls = 0
    original_find_one = repository.bookmark_operator.find_one_by_hashed_id
    original_find_tags = repository.tag_operator.find_by_bookmark_id

    def wrapped_find_one(hashed_id: str) -> BookmarkDao | None:
        # 本体 bookmark 取得クエリの呼び出し回数を追跡する。
        nonlocal bookmark_calls
        bookmark_calls += 1
        return original_find_one(hashed_id)

    def wrapped_find_tags(bookmark_id: int) -> list[TagDao]:
        # タグ解決クエリも別に数え、詳細全体が cache hit していることを確認する。
        nonlocal tag_calls
        tag_calls += 1
        return original_find_tags(bookmark_id)

    monkeypatch.setattr(repository.bookmark_operator, "find_one_by_hashed_id", wrapped_find_one)
    monkeypatch.setattr(repository.tag_operator, "find_by_bookmark_id", wrapped_find_tags)

    first = repository.find_one(hashed_id=bookmark.hashed_id)
    second = repository.find_one(hashed_id=bookmark.hashed_id)
    assert first.memo == second.memo == "before"
    assert first.tags == second.tags == ["tag1"]
    assert bookmark_calls == 1
    assert tag_calls == 1

    first.memo = "after"
    first.tags = ["tag2"]
    repository.update_one(first, current_hashed_id=bookmark.hashed_id)

    # 更新後は詳細キャッシュが無効化され、タグも含めて再取得される。
    refreshed = repository.find_one(hashed_id=bookmark.hashed_id)
    cached = repository.find_one(hashed_id=bookmark.hashed_id)
    assert refreshed.memo == cached.memo == "after"
    assert refreshed.tags == cached.tags == ["tag2"]
    assert bookmark_calls == 3
    assert tag_calls == 2


def test_bookmark_repository_find_one_not_found_is_not_cached(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    未存在ブックマークの詳細取得はキャッシュされず毎回再評価される
    """
    repository = BookmarkRepository(session, region=memory_region)

    bookmark_calls = 0
    original = repository.bookmark_operator.find_one_by_hashed_id

    def wrapped(hashed_id: str) -> BookmarkDao | None:
        # 未ヒット時もキャッシュせず、毎回 bookmark 本体を問い合わせることを見る。
        nonlocal bookmark_calls
        bookmark_calls += 1
        return original(hashed_id)

    monkeypatch.setattr(repository.bookmark_operator, "find_one_by_hashed_id", wrapped)

    with pytest.raises(BookmarkRepository.NotFoundError, match="Not found specified data."):
        repository.find_one(hashed_id="missing-bookmark")

    with pytest.raises(BookmarkRepository.NotFoundError, match="Not found specified data."):
        repository.find_one(hashed_id="missing-bookmark")

    # 例外結果はキャッシュされず、毎回 DAO が呼ばれる。
    assert bookmark_calls == 2


def test_bookmark_repository_delete_one_invalidates_detail_and_lists(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    ブックマーク削除後は詳細・一覧・タグ一覧キャッシュが無効化される
    """
    factory = UnitDataFactory(session)
    bookmark = factory.create_bookmark("https://example.com/1", "first", ["tag1"])
    factory.create_bookmark("https://example.com/2", "second", ["tag2"])
    repository = BookmarkRepository(
        session,
        page=Page(number=1, size=10),
        region=memory_region,
    )

    detail_calls = 0
    list_calls = 0
    tag_list_calls = 0
    original_find_one = repository.bookmark_operator.find_one_by_hashed_id
    original_find_all = repository.bookmark_operator.find_all
    original_find_by_tags = repository.bookmark_operator.find_by_tags

    def wrapped_find_one(hashed_id: str) -> BookmarkDao | None:
        # 詳細キャッシュの有無と、delete 時の再参照を同じカウンタで追跡する。
        nonlocal detail_calls
        detail_calls += 1
        return original_find_one(hashed_id)

    def wrapped_find_all() -> list[BookmarkDao]:
        # 全件一覧が delete 後に再評価されるかを確認する。
        nonlocal list_calls
        list_calls += 1
        return original_find_all()

    def wrapped_find_by_tags(tag_names: list[str]) -> list[BookmarkDao]:
        # タグ検索一覧も version bump で巻き込んで無効化されることを見る。
        nonlocal tag_list_calls
        tag_list_calls += 1
        return original_find_by_tags(tag_names)

    monkeypatch.setattr(repository.bookmark_operator, "find_one_by_hashed_id", wrapped_find_one)
    monkeypatch.setattr(repository.bookmark_operator, "find_all", wrapped_find_all)
    monkeypatch.setattr(repository.bookmark_operator, "find_by_tags", wrapped_find_by_tags)

    repository.find_one(hashed_id=bookmark.hashed_id)
    repository.find_one(hashed_id=bookmark.hashed_id)
    repository.find_all()
    repository.find_all()
    repository.find_by_tags(["tag1"])
    repository.find_by_tags(["tag1"])
    assert detail_calls == 1
    assert list_calls == 1
    assert tag_list_calls == 1

    repository.delete_one(hashed_id=bookmark.hashed_id)

    # delete 実行時に対象 bookmark を解決するため、詳細 DAO は 1 回追加で呼ばれる。
    assert detail_calls == 2

    with pytest.raises(BookmarkRepository.NotFoundError, match="Not found specified data."):
        repository.find_one(hashed_id=bookmark.hashed_id)

    refreshed_list = repository.find_all()
    cached_list = repository.find_all()
    refreshed_tag_list = repository.find_by_tags(["tag1"])
    cached_tag_list = repository.find_by_tags(["tag1"])

    # 削除後は詳細が見つからず、一覧系は 1 回ずつ再評価されたうえで cache hit する。
    assert detail_calls == 3
    assert sorted(bookmark.memo for bookmark in refreshed_list) == ["second"]
    assert sorted(bookmark.memo for bookmark in cached_list) == ["second"]
    assert refreshed_tag_list == cached_tag_list == []
    assert list_calls == 2
    assert tag_list_calls == 2


def test_bookmark_repository_tag_list_cache_normalizes_key_and_invalidates_on_add(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    タグ検索一覧キャッシュはタグ順を正規化し、追加後に無効化される
    """
    UnitDataFactory(session).create_bookmark("https://example.com/1", "first", ["tag1", "tag2"])
    repository = BookmarkRepository(
        session,
        page=Page(number=1, size=10),
        region=memory_region,
    )

    calls = 0
    original = repository.bookmark_operator.find_by_tags

    def wrapped(tag_names: list[str]) -> list[BookmarkDao]:
        # タグ一覧クエリの実行回数で、キー正規化と無効化の両方を確認する。
        nonlocal calls
        calls += 1
        return original(tag_names)

    monkeypatch.setattr(repository.bookmark_operator, "find_by_tags", wrapped)

    # タグ順が違っても同じ検索条件として同一キーを使う。
    first = repository.find_by_tags(["tag1", "tag2"])
    second = repository.find_by_tags(["tag2", "tag1"])
    assert sorted(bookmark.memo for bookmark in first) == ["first"]
    assert sorted(bookmark.memo for bookmark in second) == ["first"]
    assert calls == 1

    repository.add_one(
        BookmarkEntity(
            hashed_id=get_hashed_id("https://example.com/2"),
            url="https://example.com/2",
            memo="second",
            tags=["tag1", "tag2"],
        )
    )

    # add 後は tag-list version が進み、同じタグ条件でも再検索される。
    refreshed = repository.find_by_tags(["tag1", "tag2"])
    cached = repository.find_by_tags(["tag2", "tag1"])
    assert sorted(bookmark.memo for bookmark in refreshed) == ["first", "second"]
    assert sorted(bookmark.memo for bookmark in cached) == ["first", "second"]
    assert calls == 2


def test_bookmark_repository_tag_list_cache_escapes_delimiters(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    区切り文字を含むタグでも別条件の検索キーと衝突しない
    """
    factory = UnitDataFactory(session)
    factory.create_bookmark("https://example.com/1", "first", ["a,b", "c"])
    factory.create_bookmark("https://example.com/2", "second", ["a", "b,c"])
    repository = BookmarkRepository(
        session,
        page=Page(number=1, size=10),
        region=memory_region,
    )

    calls = 0
    original = repository.bookmark_operator.find_by_tags

    def wrapped(tag_names: list[str]) -> list[BookmarkDao]:
        # 条件が異なる 2 回の検索で、それぞれ別キーが使われることを確認する。
        nonlocal calls
        calls += 1
        return original(tag_names)

    monkeypatch.setattr(repository.bookmark_operator, "find_by_tags", wrapped)

    first = repository.find_by_tags(["a,b", "c"])
    second = repository.find_by_tags(["a", "b,c"])
    cached_first = repository.find_by_tags(["c", "a,b"])
    cached_second = repository.find_by_tags(["b,c", "a"])

    assert sorted(bookmark.memo for bookmark in first) == ["first"]
    assert sorted(bookmark.memo for bookmark in second) == ["second"]
    assert sorted(bookmark.memo for bookmark in cached_first) == ["first"]
    assert sorted(bookmark.memo for bookmark in cached_second) == ["second"]
    assert calls == 2


def test_bookmark_repository_tag_list_cache_normalizes_duplicate_tags(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    タグ検索一覧キャッシュは重複タグも同一条件として正規化する
    """
    UnitDataFactory(session).create_bookmark("https://example.com/1", "first", ["tag1"])
    repository = BookmarkRepository(
        session,
        page=Page(number=1, size=10),
        region=memory_region,
    )

    calls = 0
    original = repository.bookmark_operator.find_by_tags

    def wrapped(tag_names: list[str]) -> list[BookmarkDao]:
        # SQL 上は同義な ["tag1"] と ["tag1", "tag1"] が同じキーを使うことを見る。
        nonlocal calls
        calls += 1
        return original(tag_names)

    monkeypatch.setattr(repository.bookmark_operator, "find_by_tags", wrapped)

    first = repository.find_by_tags(["tag1"])
    second = repository.find_by_tags(["tag1", "tag1"])

    # 重複タグを含む条件でも、同一検索として cache hit する。
    assert sorted(bookmark.memo for bookmark in first) == ["first"]
    assert sorted(bookmark.memo for bookmark in second) == ["first"]
    assert calls == 1


def test_bookmark_repository_tag_list_cache_separates_page_size(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    タグ検索一覧キャッシュはページサイズごとに別キーになる
    """
    factory = UnitDataFactory(session)
    factory.create_bookmark("https://example.com/1", "first", ["tag1"])
    factory.create_bookmark("https://example.com/2", "second", ["tag1"])
    small_page_repository = BookmarkRepository(
        session,
        page=Page(number=1, size=1),
        region=memory_region,
    )
    large_page_repository = BookmarkRepository(
        session,
        page=Page(number=1, size=2),
        region=memory_region,
    )

    small_page_calls = 0
    large_page_calls = 0
    original_small_page = small_page_repository.bookmark_operator.find_by_tags
    original_large_page = large_page_repository.bookmark_operator.find_by_tags

    def wrapped_small_page(tag_names: list[str]) -> list[BookmarkDao]:
        # size=1 の取得が size=2 のキャッシュと混ざらないことを確認する。
        nonlocal small_page_calls
        small_page_calls += 1
        return original_small_page(tag_names)

    def wrapped_large_page(tag_names: list[str]) -> list[BookmarkDao]:
        # 同じタグ条件でもページサイズが違えば別キーで評価されることを見る。
        nonlocal large_page_calls
        large_page_calls += 1
        return original_large_page(tag_names)

    monkeypatch.setattr(small_page_repository.bookmark_operator, "find_by_tags", wrapped_small_page)
    monkeypatch.setattr(large_page_repository.bookmark_operator, "find_by_tags", wrapped_large_page)

    small_page = small_page_repository.find_by_tags(["tag1"])
    cached_small_page = small_page_repository.find_by_tags(["tag1"])
    large_page = large_page_repository.find_by_tags(["tag1"])
    cached_large_page = large_page_repository.find_by_tags(["tag1"])

    # ページサイズごとに 1 回ずつ DB を読み、同一条件では cache hit する。
    assert len(small_page) == len(cached_small_page) == 1
    assert len(large_page) == len(cached_large_page) == 2
    assert small_page_calls == 1
    assert large_page_calls == 1


def test_bookmark_repository_tag_list_cache_invalidation_reaches_all_pages(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    タグ検索一覧キャッシュの無効化は別ページ条件の一覧にも伝播する
    """
    factory = UnitDataFactory(session)
    factory.create_bookmark("https://example.com/1", "first", ["tag1"])
    factory.create_bookmark("https://example.com/2", "second", ["tag1"])
    small_page_repository = BookmarkRepository(
        session,
        page=Page(number=1, size=1),
        region=memory_region,
    )
    large_page_repository = BookmarkRepository(
        session,
        page=Page(number=1, size=2),
        region=memory_region,
    )

    small_page_calls = 0
    large_page_calls = 0
    original_small_page = small_page_repository.bookmark_operator.find_by_tags
    original_large_page = large_page_repository.bookmark_operator.find_by_tags

    def wrapped_small_page(tag_names: list[str]) -> list[BookmarkDao]:
        # 追加前後で size=1 のタグ検索一覧が再評価されるかを追跡する。
        nonlocal small_page_calls
        small_page_calls += 1
        return original_small_page(tag_names)

    def wrapped_large_page(tag_names: list[str]) -> list[BookmarkDao]:
        # tag-list version の更新が size=2 の一覧にも波及することを見る。
        nonlocal large_page_calls
        large_page_calls += 1
        return original_large_page(tag_names)

    monkeypatch.setattr(small_page_repository.bookmark_operator, "find_by_tags", wrapped_small_page)
    monkeypatch.setattr(large_page_repository.bookmark_operator, "find_by_tags", wrapped_large_page)

    small_page_repository.find_by_tags(["tag1"])
    small_page_repository.find_by_tags(["tag1"])
    large_page_repository.find_by_tags(["tag1"])
    large_page_repository.find_by_tags(["tag1"])
    assert small_page_calls == 1
    assert large_page_calls == 1

    small_page_repository.add_one(
        BookmarkEntity(
            hashed_id=get_hashed_id("https://example.com/3"),
            url="https://example.com/3",
            memo="third",
            tags=["tag1"],
        )
    )

    refreshed_small_page = small_page_repository.find_by_tags(["tag1"])
    cached_small_page = small_page_repository.find_by_tags(["tag1"])
    refreshed_large_page = large_page_repository.find_by_tags(["tag1"])
    cached_large_page = large_page_repository.find_by_tags(["tag1"])

    # tag-list namespace の version が進むと、全ページ条件で 1 回ずつ再検索される。
    assert len(refreshed_small_page) == len(cached_small_page) == 1
    assert len(refreshed_large_page) == len(cached_large_page) == 2
    assert small_page_calls == 2
    assert large_page_calls == 2


def test_bump_cache_versions_does_not_depend_on_current_version(
    session: Session,
    memory_region: CacheRegion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    正常系:
    version 更新は現在値の read-modify-write に依存せず新しい一意値へ置き換える
    """
    repository = UserRepository(session, region=memory_region)

    def fail_get_version(namespace: str) -> str:
        raise AssertionError(f"_get_cache_version should not be called during bump: {namespace}")

    monkeypatch.setattr(repository, "_get_cache_version", fail_get_version)

    repository._bump_cache_versions("list")
    first_version = repository.region.get(repository._cache_version_key("list"))
    repository._bump_cache_versions("list")
    second_version = repository.region.get(repository._cache_version_key("list"))

    assert isinstance(first_version, str)
    assert isinstance(second_version, str)
    assert first_version != second_version


def test_get_cache_version_initialization_is_atomic(session: Session) -> None:
    """
    正常系:
    初回 version 生成が並行しても同じ値に収束する
    """
    region = ConcurrentVersionRegion(parties=4)
    repository = UserRepository(session, region=region)
    versions: list[str] = []

    def worker() -> None:
        # 初期 version 生成は region.get_or_create() に集約され、並行時も 1 値だけ返る。
        versions.append(repository._get_cache_version("list"))

    threads = [Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(versions) == 4
    assert len(set(versions)) == 1
