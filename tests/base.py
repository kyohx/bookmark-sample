from src.dao.models.bookmark import BookmarkDao
from src.dao.models.bookmark_tag import BookmarkTagDao
from src.dao.models.tag import TagDao
from tests.conftest import TEST_TAG_NAME, TEST_URL, SessionForTest

from .factory import DataFactory


class BaseTest:
    def create_bookmarks(self, db_session: SessionForTest, num: int = 1) -> list[BookmarkDao]:
        """
        テスト用ブックマークを作成する

        :param db_session: DBセッション
        :param num: 作成個数
        :return: 作成したブックマークDAOのリスト
        """
        factory = DataFactory(db_session)
        return [
            factory.create_bookmark(
                url=f"{TEST_URL}/{i}",
                memo=f"Example{i}",
                tagnames=[f"{TEST_TAG_NAME}_1_{i}", f"{TEST_TAG_NAME}_2_{i}"],
            )
            for i in range(1, num + 1)
        ]

    def get_tags(self, db_session: SessionForTest, bookmark_dao: BookmarkDao) -> list[TagDao]:
        """ "
        Bookmarkに対応するタグを取得する
        """
        bookmark_tag_list = (
            db_session.query(BookmarkTagDao).filter_by(bookmark_id=bookmark_dao.id).all()
        )
        tag_id_list = [bookmark_tag.tag_id for bookmark_tag in bookmark_tag_list]
        return db_session.query(TagDao).filter(TagDao.id.in_(tag_id_list)).all()
