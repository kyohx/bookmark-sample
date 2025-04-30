from sqlalchemy import VARCHAR, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from ...libs.enum import AuthorityEnum
from .base import BaseDao, TimeStampColumnMixin


class UserDao(BaseDao, TimeStampColumnMixin):
    """
    ユーザ
    """

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    "ID"
    name: Mapped[str] = mapped_column(VARCHAR(32), unique=True)
    "ユーザー名"
    hashed_password: Mapped[str] = mapped_column(VARCHAR(64))
    "パスワードハッシュ"
    authority: Mapped[int] = mapped_column(SmallInteger, default=AuthorityEnum.READ.value)
    "権限"
    disabled: Mapped[bool] = mapped_column(default=False)
    "無効フラグ"
