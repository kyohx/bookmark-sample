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
        db_bookmarks = self.create_bookmarks(db_session, num=2)
        bookmark1 = db_bookmarks[0]

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
        updated_db_bookmarks = db_session.query(BookmarkDao).all()
        assert len(updated_db_bookmarks) == 2

        updated_db_bookmark = (
            db_session.query(BookmarkDao).filter_by(hashed_id=bookmark1.hashed_id).first()
        )
        assert updated_db_bookmark is not None
        assert updated_db_bookmark.memo == request_body["memo"]
        assert updated_db_bookmark.hashed_id == bookmark1.hashed_id

        tags = db_session.query(TagDao).filter(TagDao.name.in_(request_body["tags"])).all()
        assert len(tags) == 2
        assert set([tag.name for tag in tags]) == set(request_body["tags"])

        bookmark_tags = (
            db_session.query(BookmarkTagDao).filter_by(bookmark_id=updated_db_bookmark.id).all()
        )
        assert len(bookmark_tags) == 2
        assert set([bookmark_tag.tag_id for bookmark_tag in bookmark_tags]) == set(
            [tag.id for tag in tags]
        )
        assert set([bookmark_tag.bookmark_id for bookmark_tag in bookmark_tags]) == set(
            [updated_db_bookmark.id]
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

    def test_update_memo_only(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        メモのみ更新
        """
        bookmark = self.create_bookmarks(db_session, num=1)[0]
        db_tags = self.get_tags(db_session, bookmark)

        # リクエストボディの作成
        request_body = {"memo": "Updated"}
        # リクエストの送信
        response = client.patch(f"/bookmarks/{bookmark.hashed_id}", json=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "updated_bookmark" in response_body
        updated_bookmark = response_body["updated_bookmark"]
        assert updated_bookmark["url"] == bookmark.url
        assert updated_bookmark["memo"] == request_body["memo"]
        assert updated_bookmark["hashed_id"] == bookmark.hashed_id
        assert set(updated_bookmark["tags"]) == set([tag.name for tag in db_tags])
        assert updated_bookmark["created_at"] == datetime_to_str(bookmark.created_at)
        assert updated_bookmark["updated_at"] is not None

        # データベース内容の検証
        updated_db_bookmark = db_session.query(BookmarkDao).all()[0]

        updated_db_bookmark = (
            db_session.query(BookmarkDao).filter_by(hashed_id=bookmark.hashed_id).first()
        )
        assert updated_db_bookmark is not None
        assert updated_db_bookmark.memo == request_body["memo"]
        assert updated_db_bookmark.hashed_id == bookmark.hashed_id

        tags = db_session.query(TagDao).all()
        assert len(tags) == 2
        assert set([tag.name for tag in tags]) == set([tag.name for tag in db_tags])

        bookmark_tags = (
            db_session.query(BookmarkTagDao).filter_by(bookmark_id=updated_db_bookmark.id).all()
        )
        assert len(bookmark_tags) == 2
        assert set([bookmark_tag.tag_id for bookmark_tag in bookmark_tags]) == set(
            [tag.id for tag in tags]
        )
        assert set([bookmark_tag.bookmark_id for bookmark_tag in bookmark_tags]) == set(
            [updated_db_bookmark.id]
        )

    def test_update_tags_only(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        タグのみ更新
        """
        bookmark = self.create_bookmarks(db_session, num=1)[0]
        db_tags = self.get_tags(db_session, bookmark)

        # リクエストボディの作成
        request_body = {"tags": ["updated_tag_1", "updated_tag_2"]}
        # リクエストの送信
        response = client.patch(f"/bookmarks/{bookmark.hashed_id}", json=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "updated_bookmark" in response_body
        updated_bookmark = response_body["updated_bookmark"]
        assert updated_bookmark["url"] == bookmark.url
        assert updated_bookmark["memo"] == bookmark.memo
        assert updated_bookmark["hashed_id"] == bookmark.hashed_id
        assert set(updated_bookmark["tags"]) == set(request_body["tags"])
        assert updated_bookmark["created_at"] == datetime_to_str(bookmark.created_at)
        assert updated_bookmark["updated_at"] is not None

        # データベース内容の検証
        updated_db_bookmark = db_session.query(BookmarkDao).all()[0]
        updated_db_tags = self.get_tags(db_session, updated_db_bookmark)

        updated_db_bookmark = (
            db_session.query(BookmarkDao).filter_by(hashed_id=bookmark.hashed_id).first()
        )
        assert updated_db_bookmark is not None
        assert updated_db_bookmark.memo == bookmark.memo
        assert updated_db_bookmark.hashed_id == bookmark.hashed_id

        tags = db_session.query(TagDao).all()
        assert len(tags) == 4
        assert set([tag.name for tag in tags]) == set(request_body["tags"]) | set(
            [tag.name for tag in db_tags]
        )

        bookmark_tags = (
            db_session.query(BookmarkTagDao).filter_by(bookmark_id=updated_db_bookmark.id).all()
        )
        assert len(bookmark_tags) == 2
        assert set([bookmark_tag.tag_id for bookmark_tag in bookmark_tags]) == set(
            [tag.id for tag in updated_db_tags]
        )
        assert set([bookmark_tag.bookmark_id for bookmark_tag in bookmark_tags]) == set(
            [updated_db_bookmark.id]
        )

    def test_update_notfound(self, client: TestClient, db_session: SessionForTest):
        """ "
        異常系:
        ハッシュIDが存在しないブックマークを更新
        """
        self.create_bookmarks(db_session, num=1)

        hashed_id = "0" * 64
        # リクエストボディの作成
        request_body = {"memo": "Updated", "tags": ["updated_tag_1", "updated_tag_2"]}
        # リクエストの送信
        response = client.patch(f"/bookmarks/{hashed_id}", json=request_body)

        # レスポンスの検証
        assert response.status_code == 404

    def test_update_invalid_hashed_id(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ハッシュID不正
        """
        request_body = {"memo": "Updated", "tags": ["updated_tag_1", "updated_tag_2"]}

        # ハッシュIDの長さ不正
        hashed_id = "0" * 63
        response = client.patch(f"/bookmarks/{hashed_id}", json=request_body)
        assert response.status_code == 422

        # ハッシュIDのフォーマット不正
        hashed_id = "x" * 64
        response = client.patch(f"/bookmarks/{hashed_id}", json=request_body)
        assert response.status_code == 422

    def test_update_invalid_tags(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        タグ名指定不正
        """
        bookmark = self.create_bookmarks(db_session, num=1)[0]

        # タグ名が長い
        request_body = {"tags": ["a" * 101]}
        response = client.patch(f"/bookmarks/{bookmark.hashed_id}", json=request_body)
        assert response.status_code == 422

        # タグ名が空
        request_body = {"tags": [""]}
        response = client.patch(f"/bookmarks/{bookmark.hashed_id}", json=request_body)
        assert response.status_code == 422

        # タグ名の個数が多い
        request_body = {"tags": [f"tag_{i}" for i in range(1, 12)]}
        response = client.patch(f"/bookmarks/{bookmark.hashed_id}", json=request_body)
        assert response.status_code == 422

        # タグ名の個数が0
        request_body = {"tags": []}
        response = client.patch(f"/bookmarks/{bookmark.hashed_id}", json=request_body)
        assert response.status_code == 422

        # タグ名が重複
        request_body = {"tags": ["tag_1", "tag_1"]}
        response = client.patch(f"/bookmarks/{bookmark.hashed_id}", json=request_body)
        assert response.status_code == 422

    def test_update_invalid_memo(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        メモ指定不正
        """
        bookmark = self.create_bookmarks(db_session, num=1)[0]

        # メモが長い
        request_body = {"memo": "a" * 401}
        response = client.patch(f"/bookmarks/{bookmark.hashed_id}", json=request_body)
        assert response.status_code == 422
