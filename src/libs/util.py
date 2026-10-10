from datetime import datetime
from hashlib import sha256
from typing import Final
from zoneinfo import ZoneInfo

from ..libs.config import get_config

SALT: Final[str] = get_config().hash_salt


def get_hashed_id(value: str) -> str:
    """
    文字列からハッシュIDを返す
    """
    return sha256((value + SALT).encode()).hexdigest()


def str_to_datetime(s: str) -> datetime:
    """
    ISO 8601形式の文字列をdatetime型に変換（タイムゾーンを保持する）
    """
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        raise ValueError("illegal datetime format")
    return d


def datetime_to_str(d: datetime) -> str:
    """
    日時をタイムゾーン付き・秒精度のISO 8601形式に変換する。

    MySQLのDATETIMEなど、タイムゾーン情報のない値はDBの設定に従って解釈する。
    タイムゾーン情報のある値は元のオフセットを保持する。
    """
    if d.utcoffset() is None:
        d = d.replace(tzinfo=ZoneInfo(get_config().database_timezone))
    return d.isoformat(timespec="seconds")
