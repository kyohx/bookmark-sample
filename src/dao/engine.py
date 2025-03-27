import os
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL


@dataclass(frozen=True)
class DBConfig:
    """
    DB設定
    """

    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "root"
    name: str = "db"
    debug: bool = False


# DB設定を環境変数から取得
_config = DBConfig(
    host=os.environ.get("DATABASE_HOST", "localhost"),
    port=int(os.environ.get("DATABASE_PORT", 3306)),
    user=os.environ.get("DATABASE_USER", "root"),
    password=os.environ.get("DATABASE_PASSWORD", "root"),
    name=os.environ.get("DATABASE_NAME", "db"),
    debug=bool(int(os.environ.get("DATABASE_DEBUG", 0))),
)


# 接続先DBの設定
DATABASE = URL.create(
    "mysql+pymysql",
    username=_config.user,
    password=_config.password,
    host=_config.host,
    port=_config.port,
    database=_config.name,
)

# Engineの作成
Engine = create_engine(DATABASE, echo=_config.debug, pool_pre_ping=True)
