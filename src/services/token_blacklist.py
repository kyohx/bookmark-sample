from typing import Final

from redis.exceptions import RedisError

from ..libs.config import get_config
from ..libs.log import get_logger
from ..libs.redis_client import get_redis_client
from .base import ServiceBase, ServiceError

_logger = get_logger()
_config = get_config()


class TokenBlacklistService(ServiceBase):
    """
    リフレッシュトークンブラックリストサービス
    """

    KEY_PREFIX: Final[str] = "refresh"

    class Error(ServiceError):
        """
        ブラックリストサービスエラー
        """

        pass

    def __init__(self) -> None:
        self.redis = get_redis_client()
        self.fail_open = _config.redis_fail_open
        self.default_ttl_seconds = _config.redis_blacklist_default_ttl_days * 24 * 60 * 60

    def _handle_redis_error(self, exc: Exception, operation: str) -> None:
        """
        Redis障害時のハンドリング

        fail_open=True の場合は警告ログのみで処理継続する。

        Args:
            exc: 例外
            operation: 操作名

        Raises:
            TokenBlacklistService.Error: fail_open=Falseの場合
        """
        _logger.warning("Redis error during %s: %s", operation, exc)
        if not self.fail_open:
            raise self.Error("Redis unavailable")

    def _deny_jti_key(self, jti: str) -> str:
        """
        jti用ブラックリストキーを生成する

        Args:
            jti: トークンID

        Returns:
            Redisキー
        """
        return f"{self.KEY_PREFIX}:deny:{jti}"

    def _family_current_key(self, user: str, family: str) -> str:
        """
        user+familyの最新jti保存用キーを生成する

        Args:
            user: ユーザー名
            family: トークンファミリーID

        Returns:
            Redisキー
        """
        return f"{self.KEY_PREFIX}:family:current:{user}:{family}"

    def _family_deny_key(self, user: str, family: str) -> str:
        """
        user+family用ブラックリストキーを生成する

        Args:
            user: ユーザー名
            family: トークンファミリーID

        Returns:
            Redisキー
        """
        return f"{self.KEY_PREFIX}:family:deny:{user}:{family}"

    def is_jti_denied(self, jti: str) -> bool:
        """
        jtiがブラックリストに登録済みか確認する

        Args:
            jti: トークンID

        Returns:
            登録済みの場合はTrue、それ以外はFalse
        """
        if not self.redis:
            return False
        try:
            return bool(self.redis.exists(self._deny_jti_key(jti)))
        except RedisError as exc:
            self._handle_redis_error(exc, "is_jti_denied")
            return False

    def is_family_denied(self, user: str, family: str) -> bool:
        """
        user+familyがブラックリストに登録済みか確認する

        Args:
            user: ユーザー名
            family: トークンファミリーID

        Returns:
            登録済みの場合はTrue、それ以外はFalse
        """
        if not self.redis:
            return False
        try:
            return bool(self.redis.exists(self._family_deny_key(user, family)))
        except RedisError as exc:
            self._handle_redis_error(exc, "is_family_denied")
            return False

    def get_current_jti(self, user: str, family: str) -> str | None:
        """
        user+familyの最新jtiを取得する

        Args:
            user: ユーザー名
            family: トークンファミリーID

        Returns:
            最新のjti。未登録の場合はNone
        """
        if not self.redis:
            return None
        try:
            value = self.redis.get(self._family_current_key(user, family))
            if value is None or isinstance(value, str):
                return value
            return str(value)
        except RedisError as exc:
            self._handle_redis_error(exc, "get_current_jti")
            return None

    def set_current_jti(self, user: str, family: str, jti: str, ttl_seconds: int) -> None:
        """
        user+familyの最新jtiを保存する

        Args:
            user: ユーザー名
            family: トークンファミリーID
            jti: トークンID
            ttl_seconds: 有効期限(秒)
        """
        if not self.redis:
            return
        # 期限切れのjtiは保存しない
        if ttl_seconds <= 0:
            return
        try:
            self.redis.setex(self._family_current_key(user, family), ttl_seconds, jti)
        except RedisError as exc:
            self._handle_redis_error(exc, "set_current_jti")

    def deny_jti(self, jti: str, ttl_seconds: int | None, reason: str | None = None) -> None:
        """
        jtiをブラックリストに追加する

        Args:
            jti: トークンID
            ttl_seconds: 有効期限(秒)。未指定の場合はデフォルトTTL
            reason: 理由
        """
        if not self.redis:
            return
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        # TTLが0以下の場合は無効なため保存しない
        if ttl <= 0:
            return
        try:
            self.redis.setex(self._deny_jti_key(jti), ttl, reason or "")
        except RedisError as exc:
            self._handle_redis_error(exc, "deny_jti")

    def deny_family(
        self, user: str, family: str, ttl_seconds: int | None, reason: str | None = None
    ) -> None:
        """
        user+familyをブラックリストに追加する

        Args:
            user: ユーザー名
            family: トークンファミリーID
            ttl_seconds: 有効期限(秒)。未指定の場合はデフォルトTTL
            reason: 理由
        """
        if not self.redis:
            return
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        # TTLが0以下の場合は無効なため保存しない
        if ttl <= 0:
            return
        try:
            self.redis.setex(self._family_deny_key(user, family), ttl, reason or "")
        except RedisError as exc:
            self._handle_redis_error(exc, "deny_family")

    def remove_jti(self, jti: str) -> None:
        """
        jtiのブラックリストを削除する

        Args:
            jti: トークンID
        """
        if not self.redis:
            return
        try:
            self.redis.delete(self._deny_jti_key(jti))
        except RedisError as exc:
            self._handle_redis_error(exc, "remove_jti")

    def remove_family(self, user: str, family: str) -> None:
        """
        user+familyのブラックリストを削除する

        Args:
            user: ユーザー名
            family: トークンファミリーID
        """
        if not self.redis:
            return
        try:
            self.redis.delete(self._family_deny_key(user, family))
        except RedisError as exc:
            self._handle_redis_error(exc, "remove_family")
