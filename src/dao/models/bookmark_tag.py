from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseDao, TimeStampColumnMixin


class BookmarkTagDao(BaseDao, TimeStampColumnMixin):
    """
    ブックマークとタグの関連
    """

    __tablename__ = "bookmark_tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # ID
    bookmark_id: Mapped[int] = mapped_column(
        ForeignKey("bookmark.id"), nullable=False
    )  # ブックマークID
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), nullable=False)  # タグID
