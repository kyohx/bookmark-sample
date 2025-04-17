from sqlalchemy import delete, insert

from ..models.bookmark_tag import BookmarkTagDao
from ..models.tag import TagDao
from .base import BaseDaoOperator
from .tag import TagDaoOperator


class BookmarkTagDaoOperator(BaseDaoOperator):
    """
    ブックマークタグDAO操作クラス
    """

    MAIN_DAO = BookmarkTagDao

    def save_by_tags(self, bookmark_id: int, new_tags: list[TagDao]) -> None:
        """
        タグリストを元にブックマークタグを保存する。

        Args:
            bookmark_id: ブックマークDAOのID
            new_tags: 新しく関連付けるタグDAOのリスト
        """
        old_tags = TagDaoOperator(self.session).find_by_bookmark_id(bookmark_id)
        if set([tag.name for tag in old_tags]) == set([tag.name for tag in new_tags]):
            # タグ内容に変化がないので抜ける
            return

        # 指定されたブックマークIDの既存レコードを削除
        statement = delete(BookmarkTagDao).where(BookmarkTagDao.bookmark_id == bookmark_id)
        self.session.execute(statement)
        self.session.flush()

        if not new_tags:
            return

        # 新規レコードを追加(BULK INSERT)
        insert_records = [{"bookmark_id": bookmark_id, "tag_id": tag.id} for tag in new_tags]
        self.session.execute(insert(BookmarkTagDao), insert_records)
        self.session.flush()
