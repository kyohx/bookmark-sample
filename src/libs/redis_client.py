from redis import Redis
from redis.exceptions import RedisError

from .config import get_config
from .log import get_logger

_config = get_config()
_logger = get_logger()
_redis_client: Redis | None = None


def get_redis_client() -> Redis | None:
    """
    Redisクライアントを取得する

    Returns:
        Redisクライアント(未設定時はNone)
    """
    global _redis_client
    if not _config.redis_url:
        return None
    if _redis_client is None:
        try:
            _redis_client = Redis.from_url(_config.redis_url)
        except RedisError as exc:
            _logger.warning("Redis connection failed: %s", exc)
            return None
    return _redis_client
