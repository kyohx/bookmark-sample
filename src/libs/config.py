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
    redis_url: str
    "Redis接続URL"
    redis_fail_open: bool
    "Redis障害時のフェイルオープン設定"
    redis_blacklist_default_ttl_days: int
    "ブラックリストのデフォルトTTL(日)"

    model_config = ConfigDict(frozen=True)


load_dotenv()

env = os.environ

_refresh_days = int(env.get("REFRESH_TOKEN_EXPIRE_DAYS", 14))
_blacklist_default_ttl_days = int(env.get("REDIS_BLACKLIST_DEFAULT_TTL_DAYS", _refresh_days))

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
    redis_url=env.get("REDIS_URL", ""),
    redis_fail_open=bool(int(env.get("REDIS_FAIL_OPEN", 1))),
    redis_blacklist_default_ttl_days=_blacklist_default_ttl_days,
)


def get_config() -> Config:
    """
    設定値取得

    Returns:
        設定値
    """
    return _config
