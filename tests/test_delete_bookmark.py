from fastapi.testclient import TestClient

from src.dao.models.bookmark import BookmarkDao
from src.dao.models.bookmark_tag import BookmarkTagDao
from src.dao.models.tag import TagDao
from tests.conftest import TEST_URL, SessionForTest

from .base import BaseTest


class TestDeleteBookmark(BaseTest):
    """
    ブックマーク削除のテストクラス
    """

    def test_delete_normal(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        ブックマークを1つ削除
        """
        # テストデータ作成
        bookmarks = self.create_bookmarks(db_session, num=1)
        bookmark_id = bookmarks[0].id

        # リクエストの送信
        response = client.delete(f"/bookmarks/{bookmarks[0].hashed_id}")

        # レスポンスの検証
        assert response.status_code == 200

        # データベースの検証
        assert db_session.query(BookmarkDao).filter_by(url=TEST_URL).count() == 0
        assert db_session.query(BookmarkTagDao).filter_by(bookmark_id=bookmark_id).count() == 0
        assert db_session.query(TagDao).count() == 2  # タグは削除されない

    def test_delete_notfound(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ハッシュIDが存在しないブックマークを削除
        """
        # テストデータ作成
        self.create_bookmarks(db_session, num=1)

        hashed_id = "0" * 64

        # リクエストの送信
        response = client.delete(f"/bookmarks/{hashed_id}")

        # レスポンスの検証
        assert response.status_code == 404

    def test_add_invalid_hashed_id(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ハッシュID不正
        """
        # ハッシュIDの長さ不正
        hashed_id = "0" * 63
        response = client.delete(f"/bookmarks/{hashed_id}")
        assert response.status_code == 422

        # ハッシュIDのフォーマット不正
        hashed_id = "x" * 64
        response = client.delete(f"/bookmarks/{hashed_id}")
        assert response.status_code == 422
