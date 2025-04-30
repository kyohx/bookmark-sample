import os

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

_KEY_DEFAULT_VALUE = "28b9ecba33eb6059e3048532bf90d7bf6484ea8a3626ac2ad2fdbdc850dc89c1"


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

    model_config = ConfigDict(frozen=True)


load_dotenv()

env = os.environ

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
)


def get_config() -> Config:
    """
    設定値取得

    Returns:
        設定値
    """
    return _config
