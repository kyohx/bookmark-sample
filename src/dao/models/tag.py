from sqlalchemy import VARCHAR, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseDao, TimeStampColumnMixin


class TagDao(BaseDao, TimeStampColumnMixin):
    """
    タグ
    """

    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    "ID"
    name: Mapped[str] = mapped_column(VARCHAR(100))
    "タグ名"
