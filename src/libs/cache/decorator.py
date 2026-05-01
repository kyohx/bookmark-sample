from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, Protocol, TypeVar, cast

from dogpile.cache.api import NO_VALUE
from dogpile.cache.region import CacheRegion

from ..log import get_logger
from .key_generator import KeyFunc, KeyGenerator
from .region import NullCacheRegion
from .session_resolver import SessionResolver

P = ParamSpec("P")
T = TypeVar("T")
_logger = get_logger()


class _CacheRegionLike(Protocol):
    def get(
        self,
        key: str,
        expiration_time: float | None = None,
        ignore_expiration: bool = False,
    ) -> Any: ...

    def get_or_create(
        self,
        key: str,
        creator: Callable[[], Any],
        expiration_time: float | None = None,
    ) -> Any: ...


def query_cache(
    region: CacheRegion | NullCacheRegion | None = None,
    key_func: KeyFunc | str | None = None,
    expiration_time: int | None = None,
    session_attr: str = "session",
    region_attr: str = "region",
    unless: Callable[P, bool] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
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
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache_region = _resolve_region(region, args=args, region_attr=region_attr)
            if unless is not None and unless(*args, **kwargs):
                return func(*args, **kwargs)

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

            def creator() -> T:
                result = func(*args, **kwargs)
                session = session_resolver.resolve(args, dict(kwargs))
                if session is not None:
                    session_resolver.expunge(session, result)
                return result

            return cast(
                T,
                cache_region.get_or_create(
                    cache_key,
                    creator,
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
