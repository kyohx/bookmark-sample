from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from redis import Redis
from redis.exceptions import RedisError

from .config import get_config
from .log import get_logger

_config = get_config()
_logger = get_logger()
_blacklist_redis_client: Redis | None = None


def _merge_blacklist_redis_url_query(redis_url: str) -> str:
    parts = urlsplit(redis_url)
    query_params = parse_qsl(parts.query, keep_blank_values=True)
    existing_keys = {key for key, _ in query_params}

    if "decode_responses" not in existing_keys:
        query_params.append(("decode_responses", "True"))
    if parts.scheme == "rediss":
        if "ssl_cert_reqs" not in existing_keys:
            ssl_cert_reqs = "required" if _config.blacklist_redis_ssl_verify_cert else "none"
            query_params.append(("ssl_cert_reqs", ssl_cert_reqs))
        if _config.blacklist_redis_ssl_ca_certs and "ssl_ca_certs" not in existing_keys:
            query_params.append(("ssl_ca_certs", _config.blacklist_redis_ssl_ca_certs))
        if _config.blacklist_redis_ssl_certfile and "ssl_certfile" not in existing_keys:
            query_params.append(("ssl_certfile", _config.blacklist_redis_ssl_certfile))
        if _config.blacklist_redis_ssl_keyfile and "ssl_keyfile" not in existing_keys:
            query_params.append(("ssl_keyfile", _config.blacklist_redis_ssl_keyfile))

    new_query = urlencode(query_params, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def get_blacklist_redis_client() -> Redis | None:
    """
    ブラックリスト用Redisクライアントを取得する

    Returns:
        Redisクライアント(未設定時はNone)
    """
    global _blacklist_redis_client
    if not _config.blacklist_redis_url:
        _logger.warning("Blacklist Redis URL is not configured")
        return None
    if _blacklist_redis_client is None:
        try:
            redis_url = _merge_blacklist_redis_url_query(_config.blacklist_redis_url)
            _blacklist_redis_client = Redis.from_url(redis_url)
        except RedisError as exc:
            _logger.warning("Blacklist Redis connection failed: %s", exc)
            return None
    return _blacklist_redis_client
