import pickle  # nosec B403
from collections.abc import Iterable, Mapping, Sequence
from compression import zstd
from typing import Any

from dogpile.cache.api import NO_VALUE, BytesBackend
from dogpile.cache.backends.redis import RedisBackend
from redis.exceptions import RedisError

from ..log import get_logger

_logger = get_logger()
_DEFAULT_ZSTD_LEVEL = 3
_MIN_ZSTD_LEVEL = 1
_MAX_ZSTD_LEVEL = 22


def _normalize_zstd_level(level: int) -> int:
    """
    zstd 圧縮レベルが許容範囲内か検証する。

    Args:
        level: 検証対象の圧縮レベル

    Returns:
        正規化済みの圧縮レベル

    Raises:
        ValueError: 圧縮レベルが許容範囲外
    """
    if not _MIN_ZSTD_LEVEL <= level <= _MAX_ZSTD_LEVEL:
        raise ValueError(
            f"zstd_level must be between {_MIN_ZSTD_LEVEL} and {_MAX_ZSTD_LEVEL}: {level}"
        )
    return level


class _ZstdSerializerMixin:
    def _configure_serializers(self, zstd_level: int) -> None:
        """
        zstd 圧縮付きのシリアライザを初期化する。

        Args:
            zstd_level: zstd 圧縮レベル
        """
        self._zstd_level = _normalize_zstd_level(zstd_level)
        self.serializer = self._serialize
        self.deserializer = self._deserialize

    def _serialize(self, value: Any) -> bytes:
        """
        値を pickle 化して zstd 圧縮する。

        Args:
            value: シリアライズ対象の値

        Returns:
            圧縮済みバイト列
        """
        return zstd.compress(pickle.dumps(value), level=self._zstd_level)

    def _deserialize(self, value: bytes) -> Any:
        """
        zstd 圧縮済みデータを展開して復元する。

        Args:
            value: 圧縮済みバイト列

        Returns:
            復元した値
        """
        return pickle.loads(zstd.decompress(value))  # nosec B301


class ZstdMemoryBackend(_ZstdSerializerMixin, BytesBackend):
    def __init__(self, arguments: Mapping[str, Any]) -> None:
        """
        zstd 圧縮対応のインメモリキャッシュバックエンドを初期化する。

        Args:
            arguments: dogpile.cache から渡される設定値
        """
        cache_arguments = dict(arguments)
        self._cache: dict[str, bytes] = cache_arguments.get("cache_dict", {})
        self._configure_serializers(int(cache_arguments.get("zstd_level", _DEFAULT_ZSTD_LEVEL)))

    def get_serialized(self, key: str) -> bytes | Any:
        """
        シリアライズ済みキャッシュ値を取得する。

        Args:
            key: キャッシュキー

        Returns:
            取得した値。未登録時は `NO_VALUE`
        """
        return self._cache.get(key, NO_VALUE)

    def get_serialized_multi(self, keys: Iterable[str]) -> Sequence[bytes | Any]:
        """
        複数のシリアライズ済みキャッシュ値を取得する。

        Args:
            keys: キャッシュキー一覧

        Returns:
            各キーに対応する値一覧
        """
        return [self._cache.get(key, NO_VALUE) for key in keys]

    def set_serialized(self, key: str, value: bytes) -> None:
        """
        シリアライズ済みキャッシュ値を保存する。

        Args:
            key: キャッシュキー
            value: 保存する値
        """
        self._cache[key] = value

    def set_serialized_multi(self, mapping: Mapping[str, bytes]) -> None:
        """
        複数のシリアライズ済みキャッシュ値を保存する。

        Args:
            mapping: キャッシュキーと値の対応
        """
        for key, value in mapping.items():
            self._cache[key] = value

    def delete(self, key: str) -> None:
        """
        キャッシュ値を削除する。

        Args:
            key: 削除対象のキャッシュキー
        """
        self._cache.pop(key, None)

    def delete_multi(self, keys: Iterable[str]) -> None:
        """
        複数のキャッシュ値を削除する。

        Args:
            keys: 削除対象のキャッシュキー一覧
        """
        for key in keys:
            self._cache.pop(key, None)


class ZstdRedisBackend(_ZstdSerializerMixin, RedisBackend):
    def __init__(self, arguments: Mapping[str, Any]) -> None:
        """
        zstd 圧縮対応の Redis キャッシュバックエンドを初期化する。

        Args:
            arguments: dogpile.cache から渡される設定値
        """
        backend_arguments = dict(arguments)
        zstd_level = int(backend_arguments.pop("zstd_level", _DEFAULT_ZSTD_LEVEL))
        expiration_time = int(backend_arguments.pop("expiration_time", 3600))
        backend_arguments.setdefault("redis_expiration_time", expiration_time)
        super().__init__(backend_arguments)
        self._configure_serializers(zstd_level)

    def get_serialized(self, key: str) -> bytes | Any:
        """
        Redis からシリアライズ済みキャッシュ値を取得する。

        Args:
            key: キャッシュキー

        Returns:
            取得した値。取得失敗時は `NO_VALUE`
        """
        try:
            return super().get_serialized(key)
        except RedisError as exc:
            self._log_redis_error("get", exc)
            return NO_VALUE

    def get_serialized_multi(self, keys: Any) -> list[Any]:
        """
        Redis から複数のシリアライズ済みキャッシュ値を取得する。

        Args:
            keys: キャッシュキー一覧

        Returns:
            取得した値一覧。取得失敗時はすべて `NO_VALUE`
        """
        key_list = list(keys)
        try:
            return list(super().get_serialized_multi(key_list))
        except RedisError as exc:
            self._log_redis_error("get_multi", exc)
            return [NO_VALUE for _ in key_list]

    def set_serialized(self, key: str, value: bytes) -> None:
        """
        Redis にシリアライズ済みキャッシュ値を保存する。

        Args:
            key: キャッシュキー
            value: 保存する値
        """
        try:
            if self.redis_expiration_time:
                self.writer_client.set(key, value, ex=self.redis_expiration_time)
            else:
                self.writer_client.set(key, value)
        except RedisError as exc:
            self._log_redis_error("set", exc)

    def set_serialized_multi(self, mapping: Mapping[str, bytes]) -> None:
        """
        Redis に複数のシリアライズ済みキャッシュ値を保存する。

        Args:
            mapping: キャッシュキーと値の対応
        """
        try:
            if not self.redis_expiration_time:
                self.writer_client.mset(mapping)
                return

            pipe = self.writer_client.pipeline()
            for key, value in mapping.items():
                pipe.set(key, value, ex=self.redis_expiration_time)
            pipe.execute()
        except RedisError as exc:
            self._log_redis_error("set_multi", exc)

    def delete(self, key: str) -> None:
        """
        Redis からキャッシュ値を削除する。

        Args:
            key: 削除対象のキャッシュキー
        """
        try:
            super().delete(key)
        except RedisError as exc:
            self._log_redis_error("delete", exc)

    def delete_multi(self, keys: Any) -> None:
        """
        Redis から複数のキャッシュ値を削除する。

        Args:
            keys: 削除対象のキャッシュキー一覧
        """
        try:
            super().delete_multi(keys)
        except RedisError as exc:
            self._log_redis_error("delete_multi", exc)

    def _log_redis_error(self, operation: str, exc: RedisError) -> None:
        """
        Redis 操作失敗を警告ログに記録する。

        Args:
            operation: 失敗した操作名
            exc: 発生した例外
        """
        _logger.warning("Redis error during query cache %s: %s", operation, exc)
