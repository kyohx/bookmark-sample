from fastapi.testclient import TestClient

from src.dao.models.bookmark import BookmarkDao
from src.dao.models.bookmark_tag import BookmarkTagDao
from src.dao.models.tag import TagDao
from src.libs.util import datetime_to_str
from tests.conftest import SessionForTest

from .base import BaseTest


class TestUpdateBookmark(BaseTest):
    """
    ブックマーク更新テストクラス
    """

    def test_update_normal(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        ブックマークを1件更新
        """
        bookmarks = self.create_bookmarks(db_session, num=2)
        bookmark1 = bookmarks[0]

        # リクエストボディの作成
        request_body = {"memo": "Updated", "tags": ["updated_tag_1", "updated_tag_2"]}
        # リクエストの送信
        response = client.patch(f"/bookmarks/{bookmark1.hashed_id}", json=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "updated_bookmark" in response_body
        updated_bookmark = response_body["updated_bookmark"]
        assert updated_bookmark["url"] == bookmark1.url
        assert updated_bookmark["memo"] == request_body["memo"]
        assert updated_bookmark["hashed_id"] == bookmark1.hashed_id
        assert set(updated_bookmark["tags"]) == set(request_body["tags"])
        assert updated_bookmark["created_at"] == datetime_to_str(bookmark1.created_at)
        assert updated_bookmark["updated_at"] is not None

        # データベース内容の検証
        bookmarks = db_session.query(BookmarkDao).all()
        assert len(bookmarks) == 2

        bookmark = db_session.query(BookmarkDao).filter_by(hashed_id=bookmark1.hashed_id).first()
        assert bookmark is not None
        assert bookmark.memo == request_body["memo"]
        assert bookmark.hashed_id == bookmark1.hashed_id

        tags = db_session.query(TagDao).filter(TagDao.name.in_(request_body["tags"])).all()
        assert len(tags) == 2
        assert set([tag.name for tag in tags]) == set(request_body["tags"])

        bookmark_tags = db_session.query(BookmarkTagDao).filter_by(bookmark_id=bookmark.id).all()
        assert len(bookmark_tags) == 2
        assert set([bookmark_tag.tag_id for bookmark_tag in bookmark_tags]) == set(
            [tag.id for tag in tags]
        )
        assert set([bookmark_tag.bookmark_id for bookmark_tag in bookmark_tags]) == set(
            [bookmark.id]
        )

    def test_update_same_tags(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        他のURLと同じタグ名に更新
        """
        bookmarks = self.create_bookmarks(db_session, num=2)
        bookmark1 = bookmarks[0]

        # リクエストボディの作成
        request_body = {"memo": "Updated", "tags": ["test_tag_2_1", "test_tag_2_2"]}
        # リクエストの送信
        response = client.patch(f"/bookmarks/{bookmark1.hashed_id}", json=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "updated_bookmark" in response_body
        updated_bookmark = response_body["updated_bookmark"]
        assert updated_bookmark["url"] == bookmark1.url
        assert updated_bookmark["memo"] == request_body["memo"]
        assert updated_bookmark["hashed_id"] == bookmark1.hashed_id
        assert set(updated_bookmark["tags"]) == set(request_body["tags"])
        assert updated_bookmark["created_at"] == datetime_to_str(bookmark1.created_at)
        assert updated_bookmark["updated_at"] is not None
