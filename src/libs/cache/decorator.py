from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, Protocol, TypeVar, cast

from dogpile.cache.api import NO_VALUE
from dogpile.cache.region import CacheRegion

from ..log import get_logger
from .invalidation import has_pending_cache_invalidation
from .key_generator import KeyFunc, KeyGenerator
from .region import NullCacheRegion
from .session_resolver import SessionResolver

P = ParamSpec("P")
T = TypeVar("T")
_logger = get_logger()


class _CacheRegionLike(Protocol):
    """
    query_cache が依存する最小限のキャッシュリージョン操作を表す Protocol。
    """

    def get(
        self,
        key: str,
        expiration_time: float | None = None,
        ignore_expiration: bool = False,
    ) -> Any:
        """
        指定キーに対応するキャッシュ値を取得する。

        Args:
            key: キャッシュキー
            expiration_time: 取得時に適用する有効期間（秒）
            ignore_expiration: 有効期限の判定を省略するかどうか

        Returns:
            キャッシュ値。取得できない場合は NO_VALUE
        """
        ...

    def get_or_create(
        self,
        key: str,
        creator: Callable[[], Any],
        expiration_time: float | None = None,
    ) -> Any:
        """
        キャッシュ値を取得し、利用できない場合は生成する。

        Args:
            key: キャッシュキー
            creator: キャッシュ値を生成する関数
            expiration_time: 取得時に適用する有効期間（秒）

        Returns:
            取得または生成したキャッシュ値
        """
        ...


class _DecoratorProtocol(Protocol[P, T]):
    """
    戻り値注釈内で ParamSpec を Callable にネストしないようにするデコレータ用の Protocol
    """

    def __call__(self, func: Callable[P, T]) -> Callable[P, T]:
        """対象関数と同じシグネチャを持つラッパーを返す。"""
        ...


def query_cache(
    region: CacheRegion | NullCacheRegion | None = None,
    key_func: KeyFunc | str | None = None,
    expiration_time: int | None = None,
    session_attr: str = "session",
    region_attr: str = "region",
    unless: Callable[..., bool] | None = None,
) -> _DecoratorProtocol[P, T]:
    """
    SQLAlchemy クエリ結果をキャッシュするデコレータを返す。

    Args:
        region: 使用するキャッシュリージョン
        key_func: キャッシュキー生成関数またはテンプレート
        expiration_time: キャッシュ有効期限
        session_attr: Session を保持する属性名
        region_attr: Region を保持する属性名
        unless: True の場合にキャッシュをスキップする条件関数

    Returns:
        キャッシュ機能付きデコレータ
    """
    session_resolver = SessionResolver(session_attr=session_attr)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        """キャッシュ設定を対象関数に適用する。"""

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """キャッシュを参照し、必要に応じて対象関数を実行する。"""
            cache_region = _resolve_region(region, args=args, region_attr=region_attr)
            if unless is not None and unless(*args, **kwargs):
                return func(*args, **kwargs)

            # 戻り値の detach 判定に使う Session を先に解決しておく。
            session = session_resolver.resolve(args, dict(kwargs))

            def execute_and_prepare_result() -> T:
                """対象関数を実行し、結果に含まれる ORM オブジェクトをセッションから切り離す。"""
                result = func(*args, **kwargs)
                if session is not None:
                    # Session に紐づいた ORM オブジェクトのままキャッシュしない。
                    session_resolver.expunge(session, result)
                return result

            if has_pending_cache_invalidation(session, cache_region):
                # 同一 transaction 内で無効化待ちがある間は、stale cache の再利用/再生成を避ける。
                return execute_and_prepare_result()

            cache_key = KeyGenerator.generate(
                key_func,
                func,
                args,
                dict(kwargs),
                session_attr=session_attr,
            )
            cached = cache_region.get(cache_key, expiration_time=expiration_time)
            if cached is not NO_VALUE:
                _logger.debug("Query cache HIT: %s", cache_key)
                return cast(T, cached)

            _logger.debug("Query cache MISS: %s", cache_key)

            return cast(
                T,
                cache_region.get_or_create(
                    cache_key,
                    execute_and_prepare_result,
                    expiration_time=expiration_time,
                ),
            )

        return wrapper

    return decorator


def _resolve_region(
    region: CacheRegion | NullCacheRegion | None,
    args: tuple[object, ...],
    region_attr: str,
) -> _CacheRegionLike:
    """
    デコレータ実行時に利用するキャッシュリージョンを解決する。

    Args:
        region: デコレータ引数で指定されたリージョン
        args: ラップ対象関数の位置引数
        region_attr: インスタンスからリージョンを取得する属性名

    Returns:
        解決済みのキャッシュリージョン

    Raises:
        AttributeError: リージョンを解決できない場合
    """
    if region is not None:
        return region

    if not args:
        raise AttributeError(f"query cache region is not configured: missing args[0].{region_attr}")

    resolved_region = getattr(args[0], region_attr, None)
    if resolved_region is None:
        raise AttributeError(
            f"query cache region is not configured: missing attribute '{region_attr}'"
        )

    return cast(_CacheRegionLike, resolved_region)
