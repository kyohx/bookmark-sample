from datetime import datetime
from hashlib import sha256

from ..libs.config import get_config


SALT = get_config().hash_salt


def get_hashed_id(value: str) -> str:
    """
    文字列からハッシュIDを返す
    """
    return sha256((value + SALT).encode()).hexdigest()


def str_to_datetime(s: str) -> datetime:
    """
    文字列をdatetime型に変換
    """
    try:
        d = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise ValueError("illegal datetime format")
    return d


def datetime_to_str(d: datetime) -> str:
    """
    datetime型を文字列に変換
    """
    return d.strftime("%Y-%m-%d %H:%M:%S")
