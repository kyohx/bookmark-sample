from collections.abc import Callable
from typing import Any, TypeVar

from dogpile.cache import make_region
from dogpile.cache.api import NO_VALUE
from dogpile.cache.region import CacheRegion, register_backend

_MEMORY_BACKEND_NAME = "bookmark.zstd_memory"
_REDIS_BACKEND_NAME = "bookmark.zstd_redis"
_BACKENDS_REGISTERED = False
T = TypeVar("T")


def _register_backends() -> None:
    """
    dogpile.cache にカスタムバックエンドを登録する。
    """
    global _BACKENDS_REGISTERED
    if _BACKENDS_REGISTERED:
        return

    register_backend(_MEMORY_BACKEND_NAME, "src.libs.cache.backends", "ZstdMemoryBackend")
    register_backend(_REDIS_BACKEND_NAME, "src.libs.cache.backends", "ZstdRedisBackend")
    _BACKENDS_REGISTERED = True


def create_memory_region(expiration_time: int = 300, zstd_level: int = 3) -> CacheRegion:
    """
    zstd 圧縮対応のインメモリキャッシュリージョンを生成する。

    Args:
        expiration_time: キャッシュ有効期限
        zstd_level: zstd 圧縮レベル

    Returns:
        生成したキャッシュリージョン
    """
    _register_backends()
    return make_region().configure(
        _MEMORY_BACKEND_NAME,
        expiration_time=expiration_time,
        arguments={"zstd_level": zstd_level},
    )


def create_redis_region(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    expiration_time: int = 3600,
    zstd_level: int = 3,
) -> CacheRegion:
    """
    zstd 圧縮対応の Redis キャッシュリージョンを生成する。

    Args:
        host: Redis ホスト
        port: Redis ポート
        db: Redis DB 番号
        expiration_time: キャッシュ有効期限
        zstd_level: zstd 圧縮レベル

    Returns:
        生成したキャッシュリージョン
    """
    _register_backends()
    return make_region().configure(
        _REDIS_BACKEND_NAME,
        expiration_time=expiration_time,
        arguments={
            "host": host,
            "port": port,
            "db": db,
            "expiration_time": expiration_time,
            "zstd_level": zstd_level,
        },
    )


class NullCacheRegion:
    """
    常にキャッシュミスとして振る舞うダミーリージョン。
    """

    def get(
        self,
        key: str,
        expiration_time: float | None = None,
        ignore_expiration: bool = False,
    ) -> Any:
        """
        常に `NO_VALUE` を返す。

        Args:
            key: キャッシュキー
            expiration_time: 参照時の有効期限
            ignore_expiration: 有効期限を無視するか

        Returns:
            常に `NO_VALUE`
        """
        del key, expiration_time, ignore_expiration
        return NO_VALUE

    def get_or_create(
        self,
        key: str,
        creator: Callable[[], T],
        expiration_time: float | None = None,
    ) -> T:
        """
        キャッシュを使わずに生成関数をそのまま実行する。

        Args:
            key: キャッシュキー
            creator: 値を生成する関数
            expiration_time: 保存時の有効期限

        Returns:
            生成関数の戻り値
        """
        del key, expiration_time
        return creator()

    def set(self, key: str, value: Any, expiration_time: int | None = None) -> None:
        """
        何も保存しない。

        Args:
            key: キャッシュキー
            value: 保存対象の値
            expiration_time: 保存時の有効期限
        """
        del key, value, expiration_time

    def delete(self, key: str) -> None:
        """
        何も削除しない。

        Args:
            key: 削除対象のキャッシュキー
        """
        del key
