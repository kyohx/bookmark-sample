import os
from typing import Final

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

_KEY_DEFAULT_VALUE: Final[str] = "28b9ecba33eb6059e3048532bf90d7bf6484ea8a3626ac2ad2fdbdc850dc89c1"


class Config(BaseModel):
    """
    設定値
    """

    database_host: str
    "DBホスト名"
    database_port: int
    "DBポート番号"
    database_user: str
    "DBユーザ名"
    database_password: str
    "DBパスワード"
    database_name: str
    "DB名"
    database_debug: bool
    "DBデバッグモード"
    test_database_host: str
    "テスト用DBホスト名"
    jwt_secret_key: str
    "JWTシークレットキー"
    log_level: str
    "ログレベル"
    hash_salt: str
    "URLハッシュ化用ソルト"
    refresh_token_expire_days: int
    "リフレッシュトークンの有効期限(日)"
    access_token_expire_minutes: int
    "アクセストークンの有効期限(分)"
    cache_enabled: bool
    "クエリキャッシュ全体の有効/無効"
    cache_redis_url: str
    "クエリキャッシュ用 Redis 接続URL"
    cache_redis_expiration_time: int
    "クエリキャッシュのデフォルトTTL(秒)"
    cache_zstd_level: int
    "クエリキャッシュの zstd 圧縮レベル"
    cache_redis_ssl_verify_cert: bool
    "クエリキャッシュ用 rediss:// 使用時にSSL証明書を検証するか"
    cache_redis_ssl_ca_certs: str
    "クエリキャッシュ用 CA証明書ファイルパス"
    cache_redis_ssl_certfile: str
    "クエリキャッシュ用クライアント証明書ファイルパス (mTLS用)"
    cache_redis_ssl_keyfile: str
    "クエリキャッシュ用クライアント秘密鍵ファイルパス (mTLS用)"
    blacklist_redis_url: str
    "ブラックリスト用 Redis 接続URL"
    blacklist_redis_ssl_verify_cert: bool
    "ブラックリスト用 rediss:// 使用時にSSL証明書を検証するか"
    blacklist_redis_ssl_ca_certs: str
    "ブラックリスト用 CA証明書ファイルパス"
    blacklist_redis_ssl_certfile: str
    "ブラックリスト用クライアント証明書ファイルパス (mTLS用)"
    blacklist_redis_ssl_keyfile: str
    "ブラックリスト用クライアント秘密鍵ファイルパス (mTLS用)"
    blacklist_redis_fail_open: bool
    "ブラックリスト用 Redis 障害時のフェイルオープン設定"
    blacklist_redis_default_ttl_days: int
    "ブラックリストのデフォルトTTL(日)"

    model_config = ConfigDict(frozen=True)


load_dotenv()

env = os.environ

_refresh_days = int(env.get("REFRESH_TOKEN_EXPIRE_DAYS", 14))
_blacklist_default_ttl_days = int(env.get("BLACKLIST_REDIS_DEFAULT_TTL_DAYS", _refresh_days))

_config = Config(
    database_host=env.get("DATABASE_HOST", "localhost"),
    database_port=int(env.get("DATABASE_PORT", 3306)),
    database_user=env.get("DATABASE_USER", "root"),
    database_password=env.get("DATABASE_PASSWORD", "root"),
    database_name=env.get("DATABASE_NAME", "db"),
    database_debug=bool(int(env.get("DATABASE_DEBUG", 0))),
    test_database_host=env.get("TEST_DB_HOST", "db"),
    jwt_secret_key=env.get("JWT_SECRET_KEY", _KEY_DEFAULT_VALUE),
    log_level=env.get("LOG_LEVEL", "DEBUG"),
    hash_salt=env.get("SALT", "__SALTSALTSALT__"),
    refresh_token_expire_days=_refresh_days,
    access_token_expire_minutes=int(env.get("ACCESS_TOKEN_EXPIRE_MINUTES", 20)),
    cache_enabled=bool(int(env.get("CACHE_ENABLED", 0))),
    cache_redis_url=env.get("CACHE_REDIS_URL", ""),
    cache_redis_expiration_time=int(env.get("CACHE_REDIS_EXPIRATION_TIME", 300)),
    cache_zstd_level=int(env.get("CACHE_ZSTD_LEVEL", 3)),
    cache_redis_ssl_verify_cert=bool(int(env.get("CACHE_REDIS_SSL_VERIFY_CERT", 0))),
    cache_redis_ssl_ca_certs=env.get("CACHE_REDIS_SSL_CA_CERTS", ""),
    cache_redis_ssl_certfile=env.get("CACHE_REDIS_SSL_CERTFILE", ""),
    cache_redis_ssl_keyfile=env.get("CACHE_REDIS_SSL_KEYFILE", ""),
    blacklist_redis_url=env.get("BLACKLIST_REDIS_URL", ""),
    blacklist_redis_ssl_verify_cert=bool(int(env.get("BLACKLIST_REDIS_SSL_VERIFY_CERT", 0))),
    blacklist_redis_ssl_ca_certs=env.get("BLACKLIST_REDIS_SSL_CA_CERTS", ""),
    blacklist_redis_ssl_certfile=env.get("BLACKLIST_REDIS_SSL_CERTFILE", ""),
    blacklist_redis_ssl_keyfile=env.get("BLACKLIST_REDIS_SSL_KEYFILE", ""),
    blacklist_redis_fail_open=bool(int(env.get("BLACKLIST_REDIS_FAIL_OPEN", 1))),
    blacklist_redis_default_ttl_days=_blacklist_default_ttl_days,
)


def get_config() -> Config:
    """
    設定値取得

    Returns:
        設定値
    """
    return _config
