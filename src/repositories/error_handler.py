import pymysql.constants.ER as errcode
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError

from .base import BaseRepository


def error_handler(f):
    """
    エラーハンドラ用デコレータ
    """

    def _wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except BaseRepository.NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except (IntegrityError, OperationalError) as e:
            match e.orig.args[0]:
                case errcode.DUP_KEY | errcode.DUP_ENTRY:
                    # キー重複
                    raise HTTPException(status_code=409, detail=str(e))
                case errcode.NO_REFERENCED_ROW | errcode.NO_REFERENCED_ROW_2:
                    # 外部キー制約違反
                    raise HTTPException(status_code=424, detail=str(e))
                case errcode.LOCK_DEADLOCK:
                    # デッドロック
                    raise HTTPException(status_code=409, detail=str(e))
                case _:
                    raise

    return _wrapper
