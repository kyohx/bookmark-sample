from sqlalchemy import select

from ..models.bookmark_tag import BookmarkTagDao
from ..models.tag import TagDao
from .base import BaseDaoOperator


class TagDaoOperator(BaseDaoOperator):
    """
    タグDAO操作クラス
    """

    MAIN_DAO = TagDao

    def find_by_bookmark_id(self, bookmark_id: int) -> list[TagDao]:
        """
        ブックマークIDから関連付けられたタグDAOリストを取得する。

        Args:
            bookmark_id: 検索対象のブックマークDAO ID

        Returns:
            該当するタグDAOのリスト
        """
        statement = (
            select(TagDao)
            .join(BookmarkTagDao, BookmarkTagDao.tag_id == TagDao.id)
            .where(BookmarkTagDao.bookmark_id == bookmark_id)
            .order_by(TagDao.id)
        )
        return list(self.session.scalars(statement).all())

    def find_by_names(self, names: list[str]) -> list[TagDao]:
        """
        タグ名リストからタグDAOリストを取得する。

        Args:
            names: 検索対象のタグ名のリスト

        Returns:
            該当するタグDAOのリスト
        """
        statement = select(TagDao).where(TagDao.name.in_(names))
        return list(self.session.scalars(statement).all())

    def save_by_names(self, names: list[str]) -> None:
        """
        タグ名リストを元にタグDAOを保存する。

        Args:
            names: 保存対象のタグ名のリスト
        """
        already_exsist_tag_names = [tag.name for tag in self.find_by_names(names)]
        new_tag_names = set(names) - set(already_exsist_tag_names)
        new_tag_dao_list = [TagDao(name=tagname) for tagname in list(new_tag_names)]
        self.save(new_tag_dao_list)
