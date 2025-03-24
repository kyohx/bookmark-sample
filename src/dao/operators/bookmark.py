from sqlalchemy import select

from ..models.bookmark import BookmarkDao
from ..models.bookmark_tag import BookmarkTagDao
from ..models.tag import TagDao
from .base import BaseDaoOperator


class BookmarkDaoOperator(BaseDaoOperator):
    """
    ブックマークDAO操作クラス
    """

    MAIN_DAO = BookmarkDao

    def find_one_by_hashed_id(self, hashed_id: str) -> BookmarkDao | None:
        """
        ハッシュIDからブックマークを1件取得する
        """
        return super().find_one_by_id(hashed_id, id_column="hashed_id")

    def find_by_tags(self, tags: list[str]) -> list[BookmarkDao]:
        """
        タグ名からブックマークを複数件取得する
        """
        statement = (
            select(BookmarkDao)
            .join(BookmarkTagDao, BookmarkDao.id == BookmarkTagDao.bookmark_id)
            .join(TagDao, BookmarkTagDao.tag_id == TagDao.id)
            .where(TagDao.name.in_(tags))
            .distinct()
        )
        return list(self.session.scalars(statement).all())
