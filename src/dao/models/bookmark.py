from sqlalchemy import VARCHAR, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseDao, TimeStampColumnMixin


class BookmarkDao(BaseDao, TimeStampColumnMixin):
    """
    ブックマーク
    """

    __tablename__ = "bookmark"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # ID
    hashed_id: Mapped[str] = mapped_column(VARCHAR(64), unique=True)  # ハッシュID
    url: Mapped[str] = mapped_column(VARCHAR(400))  # URL
    memo: Mapped[str] = mapped_column(VARCHAR(400))  # メモ
