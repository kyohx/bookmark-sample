from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

from ..libs.config import get_config


_config = get_config()

# 接続先DBの設定
DATABASE = URL.create(
    "mysql+pymysql",
    username=_config.database_user,
    password=_config.database_password,
    host=_config.database_host,
    port=_config.database_port,
    database=_config.database_name,
)

# Engineの作成
Engine = create_engine(DATABASE, echo=_config.database_debug, pool_pre_ping=True)
