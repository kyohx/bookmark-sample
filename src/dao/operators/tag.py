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
        ブックマークIDからタグリストを取得
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
        タグ名リストからタグリストを取得
        """
        statement = select(TagDao).where(TagDao.name.in_(names))
        return list(self.session.scalars(statement).all())

    def save_by_names(self, names: list[str]) -> list[TagDao]:
        """
        タグ名リストからタグリストを保存
        """
        already_exsist_tag_names = [tag.name for tag in self.find_by_names(names)]
        new_tag_names = set(names) - set(already_exsist_tag_names)
        tag_dao_list = [TagDao(name=tagname) for tagname in list(new_tag_names)]
        self.save(tag_dao_list)

        return tag_dao_list
