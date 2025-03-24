import os
from datetime import datetime
from hashlib import sha256

SALT = os.environ.get("SALT", "__SALTSALTSALT__")


def get_hashed_id(value: str) -> str:
    """
    文字列からハッシュIDを返す
    """
    return sha256((value + SALT).encode()).hexdigest()


def now() -> datetime:
    """
    現在日時を返す
    """
    return datetime.now()


def none_to_empty(s: str | None) -> str:
    """
    Noneであれば空文字を返す
    """
    return s if s is not None else ""


def empty_to_none(s: str) -> str | None:
    """
    空文字であればNoneを返す
    """
    return s if s != "" else None


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
