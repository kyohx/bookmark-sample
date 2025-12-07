from sqlalchemy import select

from ..models.bookmark import BookmarkDao
from ..models.bookmark_tag import BookmarkTagDao
from ..models.tag import TagDao
from .base import BaseDaoOperator


class BookmarkDaoOperator(BaseDaoOperator[BookmarkDao]):
    """
    ブックマークDAO操作クラス
    """

    MAIN_DAO = BookmarkDao

    def find_one_by_hashed_id(self, hashed_id: str) -> BookmarkDao | None:
        """
        ハッシュIDからブックマークDAOを1件取得する。

        Args:
            hashed_id: 検索対象のハッシュID

        Returns:
            取得したブックマークDAO、または見つからない場合はNone
        """
        return super().find_one_by_id(hashed_id, id_column="hashed_id")

    def find_by_tags(self, tags: list[str]) -> list[BookmarkDao]:
        """
        タグ名リストからブックマークDAOを複数件取得する。

        Args:
            tags: 検索対象のタグ名のリスト

        Returns:
            該当するブックマークDAOのリスト
        """
        statement = (
            select(BookmarkDao)
            .join(BookmarkTagDao, BookmarkDao.id == BookmarkTagDao.bookmark_id)
            .join(TagDao, BookmarkTagDao.tag_id == TagDao.id)
            .where(TagDao.name.in_(tags))
            .distinct()
        )
        statement = self.pagenation(statement)
        return list(self.session.scalars(statement).all())
