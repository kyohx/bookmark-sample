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

# KEYS: 最新jti、family拒否、旧jti拒否、セッション、ユーザーのセッション一覧。
# ARGV: 旧jti、新jti、旧トークン期限、新トークン期限、family。
# 照会と書き込みの間に別のrefresh/revokeが割り込まないよう、すべてRedis内で行う。
_ROTATE_REFRESH_TOKEN_SCRIPT: Final[str] = """
local now = tonumber(redis.call('TIME')[1])
local old_expires_at = tonumber(ARGV[3])
local new_expires_at = tonumber(ARGV[4])
if old_expires_at <= now or new_expires_at <= now then
    return 0
end
if redis.call('EXISTS', KEYS[2]) == 1
    or redis.call('HGET', KEYS[4], 'revoked') == '1' then
    return 0
end

local current_jti = redis.call('GET', KEYS[1])
if current_jti and current_jti ~= ARGV[1] then
    -- 新しいトークンの期限までfamilyを拒否し、旧トークンの再利用を防ぐ。
    local session_expires_at = tonumber(redis.call('HGET', KEYS[4], 'expires_at')) or 0
    local deny_until = math.max(
        old_expires_at, session_expires_at,
        now + math.max(redis.call('TTL', KEYS[1]), 0), now + 1
    )
    redis.call('SET', KEYS[2], 'reuse detected', 'EXAT', deny_until)
    redis.call('SET', KEYS[3], 'reuse detected', 'EXAT', old_expires_at)
    if redis.call('EXISTS', KEYS[4]) == 1 then
        redis.call('HSET', KEYS[4], 'revoked', 1)
    end
    return 0
end
if redis.call('EXISTS', KEYS[3]) == 1 then
    return 0
end

redis.call('SET', KEYS[3], 'rotated', 'EXAT', old_expires_at)
redis.call('SET', KEYS[1], ARGV[2], 'EXAT', new_expires_at)
-- デプロイ前に発行されたトークンも、初回更新後は台帳に登録する。
redis.call('HSETNX', KEYS[4], 'created_at', now)
redis.call('HSETNX', KEYS[4], 'revoked', 0)
redis.call('HSETNX', KEYS[4], 'user_agent', '')
redis.call('HSET', KEYS[4], 'last_used_at', now, 'expires_at', new_expires_at)
redis.call('EXPIREAT', KEYS[4], new_expires_at)
redis.call('ZADD', KEYS[5], new_expires_at, ARGV[5])
if redis.call('TTL', KEYS[5]) < new_expires_at - now then
    redis.call('EXPIREAT', KEYS[5], new_expires_at)
end
return 1
"""


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

    def rotate_refresh_token(
        self,
        user: str,
        family: str,
        old_jti: str,
        new_jti: str,
        old_expires_at: int,
        new_expires_at: int,
    ) -> bool:
        """旧トークンの検証・失効、新jtiと台帳の更新を原子的に行う。

        拒否・再利用・期限切れはFalse。Redis障害時は既存のfail-open設定に従う。
        最新jtiが未登録の旧セッションも、初回更新時に登録する。
        """
        redis = self.redis
        if redis is None:
            self._handle_redis_error(RedisError("Redis unavailable"), "rotate_refresh_token")
            return True
        try:
            return (
                redis.eval(
                    _ROTATE_REFRESH_TOKEN_SCRIPT,
                    5,
                    self._family_current_key(user, family),
                    self._family_deny_key(user, family),
                    self._deny_jti_key(old_jti),
                    self._session_key(user, family),
                    self._sessions_key(user),
                    old_jti,
                    new_jti,
                    old_expires_at,
                    new_expires_at,
                    family,
                )
                == 1
            )
        except RedisError as exc:
            self._handle_redis_error(exc, "rotate_refresh_token")
            return True

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
