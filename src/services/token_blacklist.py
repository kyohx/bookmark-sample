from datetime import UTC, datetime
from typing import Final

from redis.exceptions import RedisError

from ..entities.session import RefreshSession
from ..libs.config import get_config
from ..libs.log import get_logger
from ..libs.redis_client import get_blacklist_redis_client
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
        self.redis = get_blacklist_redis_client()
        self.fail_open = _config.blacklist_redis_fail_open
        self.default_ttl_seconds = _config.blacklist_redis_default_ttl_days * 24 * 60 * 60

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

    def _session_key(self, user: str, family: str) -> str:
        return f"{self.KEY_PREFIX}:session:{user}:{family}"

    def _sessions_key(self, user: str) -> str:
        return f"{self.KEY_PREFIX}:sessions:{user}"

    def _require_redis(self):
        if self.redis is None:
            raise self.Error("Redis unavailable")
        return self.redis

    def record_session(
        self, user: str, family: str, expires_at: int, user_agent: str | None = None
    ) -> None:
        """ログイン時のセッションを登録し、一覧から参照可能にする。"""
        redis = self._require_redis()
        now = int(datetime.now(UTC).timestamp())
        ttl = max(expires_at - now, 1)
        try:
            with redis.pipeline() as pipe:
                pipe.hset(
                    self._session_key(user, family),
                    mapping={
                        "created_at": now,
                        "last_used_at": now,
                        "expires_at": expires_at,
                        "revoked": 0,
                        "user_agent": (user_agent or "")[:256],
                    },
                )
                pipe.expire(self._session_key(user, family), ttl)
                pipe.zadd(self._sessions_key(user), {family: expires_at})
                pipe.expire(self._sessions_key(user), ttl)
                pipe.execute()
        except RedisError as exc:
            raise self.Error("Redis unavailable") from exc

    def touch_session(self, user: str, family: str, expires_at: int) -> None:
        """ローテーション後のセッションの最終利用日時と期限を更新する。"""
        redis = self._require_redis()
        now = int(datetime.now(UTC).timestamp())
        ttl = max(expires_at - now, 1)
        try:
            with redis.pipeline() as pipe:
                # デプロイ前に発行されたトークンも、更新後は一覧に載せる。
                pipe.hsetnx(self._session_key(user, family), "created_at", now)
                pipe.hsetnx(self._session_key(user, family), "revoked", 0)
                pipe.hsetnx(self._session_key(user, family), "user_agent", "")
                pipe.hset(
                    self._session_key(user, family),
                    mapping={"last_used_at": now, "expires_at": expires_at},
                )
                pipe.expire(self._session_key(user, family), ttl)
                pipe.zadd(self._sessions_key(user), {family: expires_at})
                pipe.expire(self._sessions_key(user), ttl)
                pipe.execute()
        except RedisError as exc:
            raise self.Error("Redis unavailable") from exc

    def list_sessions(self, user: str) -> list[RefreshSession]:
        """指定ユーザーの有効期限内のセッションを取得する。"""
        redis = self._require_redis()
        now = int(datetime.now(UTC).timestamp())
        try:
            redis.zremrangebyscore(self._sessions_key(user), "-inf", now)
            families = redis.zrange(self._sessions_key(user), 0, -1)
            sessions = []
            for family in families:
                if isinstance(family, bytes):
                    family = family.decode()
                if not isinstance(family, str):
                    continue
                data = redis.hgetall(self._session_key(user, family))
                if not data:
                    redis.zrem(self._sessions_key(user), family)
                    continue
                data = {
                    key.decode() if isinstance(key, bytes) else key: value.decode()
                    if isinstance(value, bytes)
                    else value
                    for key, value in data.items()
                }
                sessions.append(
                    RefreshSession(
                        id=family,
                        created_at=datetime.fromtimestamp(int(data["created_at"]), UTC),
                        last_used_at=datetime.fromtimestamp(int(data["last_used_at"]), UTC),
                        expires_at=datetime.fromtimestamp(int(data["expires_at"]), UTC),
                        revoked=data["revoked"] == "1",
                        user_agent=data["user_agent"] or None,
                    )
                )
            return sorted(sessions, key=lambda session: session.created_at, reverse=True)
        except RedisError as exc:
            raise self.Error("Redis unavailable") from exc

    def revoke_session(self, user: str, family: str) -> bool:
        """存在する family のリフレッシュトークンを期限まで拒否する。"""
        redis = self._require_redis()
        try:
            data = redis.hgetall(self._session_key(user, family))
            if not data:
                return False
            expires_at = data.get("expires_at", data.get(b"expires_at"))
            if expires_at is None:
                raise self.Error("Session metadata unavailable")
            now = int(datetime.now(UTC).timestamp())
            # 並行中のリフレッシュが新しいトークンを発行しても失効状態を維持する。
            ttl = max(int(expires_at) - now, _config.refresh_token_expire_days * 86400, 1)
            with redis.pipeline() as pipe:
                pipe.set(self._family_deny_key(user, family), "session revoked", ex=ttl)
                pipe.hset(self._session_key(user, family), "revoked", 1)
                pipe.execute()
            return True
        except RedisError as exc:
            raise self.Error("Redis unavailable") from exc

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
            self.redis.set(self._family_current_key(user, family), jti, ex=ttl_seconds)
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
            self.redis.set(self._deny_jti_key(jti), reason or "", ex=ttl)
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
            self.redis.set(self._family_deny_key(user, family), reason or "", ex=ttl)
            if self.redis.exists(self._session_key(user, family)):
                self.redis.hset(self._session_key(user, family), "revoked", 1)
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
