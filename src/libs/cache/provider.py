from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit

from dogpile.cache.region import CacheRegion

from ..config import Config, get_config
from ..log import get_logger
from .region import NullCacheRegion, create_redis_region

_logger = get_logger()


def _build_connection_kwargs(config: Config) -> dict[str, Any]:
    connection_kwargs: dict[str, Any] = {}
    if urlsplit(config.cache_redis_url).scheme != "rediss":
        return connection_kwargs

    # blacklist 用 Redis 設定と分離した cache 用 SSL 設定だけをここで組み立てる。
    connection_kwargs["ssl_cert_reqs"] = (
        "required" if config.cache_redis_ssl_verify_cert else "none"
    )
    if config.cache_redis_ssl_ca_certs:
        connection_kwargs["ssl_ca_certs"] = config.cache_redis_ssl_ca_certs
    if config.cache_redis_ssl_certfile:
        connection_kwargs["ssl_certfile"] = config.cache_redis_ssl_certfile
    if config.cache_redis_ssl_keyfile:
        connection_kwargs["ssl_keyfile"] = config.cache_redis_ssl_keyfile
    return connection_kwargs


@lru_cache
def get_query_cache_region() -> CacheRegion | NullCacheRegion:
    config = get_config()
    if not config.cache_enabled:
        return NullCacheRegion()

    if not config.cache_redis_url:
        _logger.warning("Query cache is enabled but CACHE_REDIS_URL is not configured")
        return NullCacheRegion()

    # Region はプロセス内で共有し、repository ごとに同じ backend を使い回す。
    connection_kwargs = _build_connection_kwargs(config)
    return create_redis_region(
        url=config.cache_redis_url,
        expiration_time=config.cache_redis_expiration_time,
        zstd_level=config.cache_zstd_level,
        connection_kwargs=connection_kwargs or None,
    )
