from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from redis import Redis
from redis.exceptions import RedisError

from .config import get_config
from .log import get_logger

_config = get_config()
_logger = get_logger()
_redis_client: Redis | None = None


def _merge_redis_url_query(redis_url: str) -> str:
    parts = urlsplit(redis_url)
    query_params = parse_qsl(parts.query, keep_blank_values=True)
    existing_keys = {key for key, _ in query_params}

    if "decode_responses" not in existing_keys:
        query_params.append(("decode_responses", "True"))
    if parts.scheme == "rediss" and "ssl_cert_reqs" not in existing_keys:
        query_params.append(("ssl_cert_reqs", "none"))

    new_query = urlencode(query_params, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def get_redis_client() -> Redis | None:
    """
    Redisクライアントを取得する

    Returns:
        Redisクライアント(未設定時はNone)
    """
    global _redis_client
    if not _config.redis_url:
        _logger.warning("Redis URL is not configured")
        return None
    if _redis_client is None:
        try:
            redis_url = _merge_redis_url_query(_config.redis_url)
            print(f"Connecting to Redis at {redis_url}")
            _redis_client = Redis.from_url(redis_url)
        except RedisError as exc:
            _logger.warning("Redis connection failed: %s", exc)
            return None
    return _redis_client
