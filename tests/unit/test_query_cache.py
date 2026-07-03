from collections.abc import Iterator

import pytest
from dogpile.cache.api import NO_VALUE
from dogpile.cache.region import CacheRegion
from redis.backoff import NoBackoff
from redis.retry import Retry
from sqlalchemy import Integer, String, inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from src.libs.cache import NullCacheRegion, create_memory_region, create_redis_region, query_cache
from src.libs.cache.key_generator import KeyGenerator
from src.libs.cache.session_resolver import SessionResolver


class Base(DeclarativeBase):
    pass


class Widget(Base):
    __tablename__ = "widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))


@pytest.fixture
def session(sqlite_session_factory) -> Iterator[Session]:
    with sqlite_session_factory(Base.metadata) as db_session:
        yield db_session


def _create_widget(session: Session, name: str = "cached") -> int:
    # テスト用の Widget を 1 件作成する
    widget = Widget(name=name)
    session.add(widget)
    session.commit()
    assert widget.id is not None
    return widget.id


def _require_widget(widget: Widget | None) -> Widget:
    # 取得結果が None でないことを型付きで保証する
    assert widget is not None
    return widget


def test_default_key_skips_session_argument(session: Session) -> None:
    """
    正常系:
    Session 引数を除外してデフォルトキーを生成
    """

    # テスト対象関数の定義
    def load_widget(db: Session, widget_id: int, include_deleted: bool = False) -> None:
        del db, widget_id, include_deleted

    # キャッシュキーの生成
    key = KeyGenerator.default(load_widget, (session, 7), {"include_deleted": True})

    # Session を含めず、引数本体だけでキーが生成されることを検証
    assert key == (
        f"{load_widget.__module__}.{load_widget.__qualname__}:(7,):{{'include_deleted': True}}"
    )


def test_default_key_skips_self_with_session_attr(session: Session) -> None:
    """
    正常系:
    session_attr を持つ self を除外してデフォルトキーを生成
    """

    class Repository:
        def __init__(self, db: Session) -> None:
            self.db: Session = db

        def load(self, widget_id: int) -> None:
            del widget_id

    # テストデータの準備
    repository = Repository(session)

    # キャッシュキーの生成
    key = KeyGenerator.default(Repository.load, (repository, 9), {}, session_attr="db")

    # self を含めずにキーが生成されることを検証
    assert key == f"{Repository.load.__module__}.{Repository.load.__qualname__}:(9,):{{}}"


def test_template_key_generator_binds_argument_names(session: Session) -> None:
    """
    正常系:
    テンプレートキー生成が関数引数名に束縛される
    """

    # テスト対象関数の定義
    def load_widget(db: Session, widget_id: int, include_deleted: bool = False) -> None:
        del db, widget_id, include_deleted

    # テンプレートキー生成関数の作成
    key_func = KeyGenerator.from_template("widget:{widget_id}:{include_deleted}", load_widget)

    # デフォルト引数も含めてテンプレートが展開されることを検証
    assert key_func(session, 7) == "widget:7:False"


def test_default_key_sorts_keyword_arguments(session: Session) -> None:
    """
    正常系:
    デフォルトキー生成は kwargs の順序差を正規化する
    """

    # テスト対象関数の定義
    def load_widget(
        db: Session, widget_id: int, include_deleted: bool = False, limit: int = 10
    ) -> None:
        del db, widget_id, include_deleted, limit

    # kwargs の投入順が違っても、同じキーに正規化されることを確認する。
    first = KeyGenerator.default(
        load_widget,
        (session, 7),
        {"include_deleted": True, "limit": 20},
    )
    second = KeyGenerator.default(
        load_widget,
        (session, 7),
        {"limit": 20, "include_deleted": True},
    )

    assert first == second


def test_query_cache_caches_detached_model(session: Session, memory_region: CacheRegion) -> None:
    """
    正常系:
    query_cache が detached な ORM オブジェクトをキャッシュする
    """

    # キャッシュリージョンとテストデータの準備
    region = memory_region
    widget_id = _create_widget(session)

    class Repository:
        def __init__(self, db: Session) -> None:
            self.session: Session = db
            self.region = region
            self.calls: int = 0

        @query_cache(key_func="widget:{widget_id}")
        def get_by_id(self, widget_id: int) -> Widget | None:
            self.calls += 1
            return self.session.get(Widget, widget_id)

    # テスト対象の準備
    repository = Repository(session)

    # 1 回目で DB 参照、2 回目でキャッシュ参照
    first = repository.get_by_id(widget_id=widget_id)
    second = repository.get_by_id(widget_id=widget_id)
    first_widget = _require_widget(first)
    second_widget = _require_widget(second)

    # レスポンスとキャッシュ動作の検証
    assert repository.calls == 1
    assert first_widget is not second_widget
    assert first_widget.id == second_widget.id == widget_id
    assert sa_inspect(first_widget).detached
    assert sa_inspect(second_widget).detached


def test_query_cache_caches_none_result(memory_region: CacheRegion) -> None:
    """
    正常系:
    query_cache は None も有効なキャッシュ値として保持する
    """

    # キャッシュリージョンの準備
    region = memory_region
    calls = 0

    # テスト対象関数の定義
    @query_cache(region=region, key_func="widget:{widget_id}")
    def load_widget(widget_id: int) -> Widget | None:
        nonlocal calls
        calls += 1
        return None

    first = load_widget(7)
    second = load_widget(7)

    # None は miss 扱いされず、2 回目は関数本体を再実行しない。
    assert first is None
    assert second is None
    assert calls == 1


def test_query_cache_caches_empty_list(memory_region: CacheRegion) -> None:
    """
    正常系:
    query_cache は空リストも有効なキャッシュ値として保持する
    """

    # キャッシュリージョンの準備
    region = memory_region
    calls = 0

    # テスト対象関数の定義
    @query_cache(region=region, key_func="widgets:{prefix}")
    def load_widgets(prefix: str) -> list[Widget]:
        nonlocal calls
        calls += 1
        return []

    first = load_widgets("missing")
    second = load_widgets("missing")

    # 空リストも miss 扱いされず、2 回目は cache hit する。
    assert first == []
    assert second == []
    assert calls == 1


def test_query_cache_supports_custom_session_and_region_attributes(session: Session) -> None:
    """
    正常系:
    カスタム属性名で Session と Region を解決できる
    """

    # キャッシュリージョンとテストデータの準備
    region = create_memory_region()
    widget_id = _create_widget(session)

    class Repository:
        def __init__(self, db: Session) -> None:
            self.db: Session = db
            self.cache = region
            self.calls: int = 0

        @query_cache(key_func="widget:{widget_id}", session_attr="db", region_attr="cache")
        def get_by_id(self, widget_id: int) -> Widget | None:
            self.calls += 1
            return self.db.get(Widget, widget_id)

    # テスト対象の準備
    repository = Repository(session)

    # 1 回目で DB 参照、2 回目でキャッシュ参照
    first = repository.get_by_id(widget_id)
    second = repository.get_by_id(widget_id)
    first_widget = _require_widget(first)
    second_widget = _require_widget(second)

    # カスタム属性名でもキャッシュが機能することを検証
    assert repository.calls == 1
    assert first_widget.id == second_widget.id == widget_id


def test_query_cache_supports_function_style_with_session_argument(
    session: Session, memory_region: CacheRegion
) -> None:
    """
    正常系:
    関数スタイルでも Session 引数からキャッシュできる
    """

    # キャッシュリージョンとテストデータの準備
    region = memory_region
    widget_id = _create_widget(session)
    calls = 0

    # テスト対象関数の定義
    @query_cache(region=region, key_func=lambda db, widget_id: f"widget:{widget_id}")
    def load_widget(db: Session, widget_id: int) -> Widget | None:
        nonlocal calls
        calls += 1
        return db.get(Widget, widget_id)

    # 1 回目で DB 参照、2 回目でキャッシュ参照
    first = load_widget(session, widget_id)
    second = load_widget(session, widget_id)
    first_widget = _require_widget(first)
    second_widget = _require_widget(second)

    # 関数スタイルでもキャッシュと expunge が機能することを検証
    assert calls == 1
    assert first_widget.id == second_widget.id == widget_id
    assert sa_inspect(first_widget).detached
    assert sa_inspect(second_widget).detached


def test_unless_skips_cache(memory_region: CacheRegion) -> None:
    """
    正常系:
    unless 条件が True の場合はキャッシュをスキップ
    """

    # キャッシュリージョンの準備
    region = memory_region
    calls = 0

    # テスト対象関数の定義
    @query_cache(region=region, key_func="value:{value}", unless=lambda value: value > 0)
    def double(value: int) -> int:
        nonlocal calls
        calls += 1
        return value * 2

    # 関数の実行
    assert double(5) == 10
    assert double(5) == 10

    # 毎回本体が実行され、キャッシュされないことを検証
    assert calls == 2


def test_null_cache_region_never_caches() -> None:
    """
    正常系:
    NullCacheRegion 利用時は常にキャッシュミスになる
    """

    # NullCacheRegion の準備
    region = NullCacheRegion()
    calls = 0

    # テスト対象関数の定義
    @query_cache(region=region, key_func="value:{value}")
    def double(value: int) -> int:
        nonlocal calls
        calls += 1
        return value * 2

    # 関数の実行
    assert double(3) == 6
    assert double(3) == 6

    # 毎回本体が実行され、Region に値が保存されないことを検証
    assert calls == 2
    assert region.get("value:3") is NO_VALUE


def test_missing_region_attribute_raises_attribute_error() -> None:
    """
    異常系:
    Region 属性を解決できない場合は AttributeError
    """

    # Region を持たないテスト対象の定義
    class Repository:
        @query_cache()
        def load(self, value: int) -> int:
            return value

    # テスト対象の準備
    repository = Repository()

    # 例外の検証
    with pytest.raises(AttributeError, match="region"):
        repository.load(1)


def test_session_resolver_expunge_handles_collections(session: Session) -> None:
    """
    正常系:
    SessionResolver がコレクション要素を expunge できる
    """

    # テストデータの準備
    widget_id = _create_widget(session)
    widgets = [session.get(Widget, widget_id)]
    resolver = SessionResolver()

    # expunge の実行
    resolver.expunge(session, widgets)
    resolver.expunge(session, widgets)

    # コレクション要素が detached になることを検証
    assert widgets[0] is not None
    assert sa_inspect(widgets[0]).detached


def test_memory_backend_stores_compressed_bytes() -> None:
    """
    正常系:
    メモリバックエンド内部では圧縮済み bytes を保持する
    """

    # キャッシュリージョンとテストデータの準備
    region = create_memory_region()
    payload = {"value": "x" * 256}

    # キャッシュへの保存
    region.set("payload", payload)

    # 復元値と内部保存形式の検証
    assert region.get("payload") == payload
    assert isinstance(region.backend._cache["payload"], bytes)


def test_redis_backend_fails_open_when_redis_is_unavailable() -> None:
    """
    正常系:
    Redis 障害時はフェイルオープンで関数本体を実行する
    """

    # 到達不能な Redis を指定した Region の準備
    region = create_redis_region(
        host="127.0.0.1",
        port=1,
        db=0,
        expiration_time=1,
        connection_kwargs={
            "retry": Retry(NoBackoff(), 0),
            "socket_connect_timeout": 0.01,
            "socket_timeout": 0.01,
        },
    )
    calls = 0

    # テスト対象関数の定義
    @query_cache(region=region, key_func="value:{value}")
    def double(value: int) -> int:
        nonlocal calls
        calls += 1
        return value * 2

    # 関数の実行
    assert double(4) == 8
    assert double(4) == 8

    # 例外にせず毎回本体が実行されることを検証
    assert calls == 2
