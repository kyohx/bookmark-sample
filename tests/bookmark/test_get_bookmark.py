from fastapi.testclient import TestClient

from src.libs.util import datetime_to_str
from src.main import app
from tests.conftest import SessionForTest

from ..base import BaseTest


class TestGetBookmark(BaseTest):
    """
    ブックマーク取得テストクラス
    """

    def api_path(self, hashed_id: str) -> str:
        return app.url_path_for("get_bookmark", hashed_id=hashed_id)

    def test_get_one_normal(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        ブックマークを1つ取得
        """
        bookmarks = self.create_bookmarks(db_session, num=2)
        db_bookmark = bookmarks[0]

        # リクエストの送信
        response = client.get(self.api_path(db_bookmark.hashed_id))

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmark" in response_body
        res_bookmark = response_body["bookmark"]
        assert res_bookmark["url"] == db_bookmark.url
        assert res_bookmark["memo"] == db_bookmark.memo
        assert res_bookmark["hashed_id"] == db_bookmark.hashed_id
        assert set(res_bookmark["tags"]) == set(
            [tag.name for tag in self.get_tags(db_session, db_bookmark)]
        )
        assert res_bookmark["created_at"] == datetime_to_str(db_bookmark.created_at)
        assert res_bookmark["updated_at"] == datetime_to_str(db_bookmark.updated_at)

    def test_get_one_notfound(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        ハッシュIDが存在しないブックマーク取得
        """
        # テストデータ作成
        self.create_bookmarks(db_session, num=1)

        hashed_id = "0" * 64

        # リクエストの送信
        response = client.get(self.api_path(hashed_id))

        # レスポンスの検証
        assert response.status_code == 404

    def test_get_invalid_hashed_id(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        ハッシュID不正
        """
        # ハッシュIDの長さ不正
        hashed_id = "0" * 63
        response = client.get(self.api_path(hashed_id))
        assert response.status_code == 422

        # ハッシュIDのフォーマット不正
        hashed_id = "x" * 64
        response = client.get(self.api_path(hashed_id))
        assert response.status_code == 422
