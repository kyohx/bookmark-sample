from fastapi.testclient import TestClient

from src.dao.models.bookmark import BookmarkDao
from src.dao.models.bookmark_tag import BookmarkTagDao
from src.dao.models.tag import TagDao
from tests.conftest import TEST_TAGS, TEST_URL, SessionForTest

from .base import BaseTest


class TestAddBookmark(BaseTest):
    """
    ブックマーク追加のテストクラス
    """

    def test_add_normal(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        ブックマークを1つ追加
        """
        assert db_session.query(BookmarkDao).where(BookmarkDao.url == TEST_URL).count() == 0

        # リクエストボディの作成
        request_body = {
            "url": TEST_URL,
            "memo": "テストメモ",
            "tags": TEST_TAGS,
        }

        # リクエストの送信
        response = client.post("/bookmarks", json=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "hashed_id" in response_body
        hashed_id = response_body["hashed_id"]
        assert len(hashed_id) == 64

        # データベースの検証
        bookmarks = db_session.query(BookmarkDao).filter_by(url=TEST_URL).all()
        assert len(bookmarks) == 1
        bookmark = bookmarks[0]
        assert bookmark.url == request_body["url"]
        assert bookmark.memo == request_body["memo"]
        assert bookmark.hashed_id == hashed_id

        tags = db_session.query(TagDao).filter(TagDao.name.in_(TEST_TAGS)).all()
        assert len(tags) == len(TEST_TAGS)
        assert set([tag.name for tag in tags]) == set(TEST_TAGS)

        bookmark_tags = db_session.query(BookmarkTagDao).filter_by(bookmark_id=bookmark.id).all()
        assert len(bookmark_tags) == len(TEST_TAGS)
        assert set([bookmark_tag.tag_id for bookmark_tag in bookmark_tags]) == set(
            [tag.id for tag in tags]
        )
        assert set([bookmark_tag.bookmark_id for bookmark_tag in bookmark_tags]) == set(
            [bookmark.id]
        )

    def test_add_duplicate(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ブックマーク重複追加
        """
        ## 追加
        request_body = {
            "url": TEST_URL,
            "memo": "テストメモ",
            "tags": TEST_TAGS,
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 200

        ## 同じブックマーク情報を追加
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 409

    def test_add_invalid_url(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ブックマークURL不正
        """
        # URLの指定なし
        request_body = {
            "memo": "テストメモ",
            "tags": TEST_TAGS,
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 422

        # 不正なURL
        request_body = {
            "url": "invalid_url",
            "memo": "テストメモ",
            "tags": TEST_TAGS,
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 422

        # URLの長さが400文字を超える
        path = "a" * (401 - (len(TEST_URL) + 1))
        url = f"{TEST_URL}/{path}"
        assert len(url) == 401
        request_body = {
            "url": url,
            "memo": "テストメモ",
            "tags": TEST_TAGS,
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 422

    def test_add_invalid_memo(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ブックマークメモ不正
        """
        # メモの指定なし
        request_body = {
            "url": TEST_URL,
            "tags": TEST_TAGS,
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 422

        # メモの長さが400文字を超える
        request_body = {
            "url": "invalid_url",
            "memo": "a" * 401,
            "tags": TEST_TAGS,
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 422

    def test_add_invalid_tags(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ブックマークタグ不正
        """
        # タグ指定なし
        request_body = {
            "url": TEST_URL,
            "memo": "テストメモ",
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 422

        # タグが空
        request_body = {
            "url": TEST_URL,
            "memo": "テストメモ",
            "tags": [],
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 422

        # タグ名が空
        request_body = {
            "url": TEST_URL,
            "memo": "テストメモ",
            "tags": ["", "tag"],
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 422

        # タグ名がユニークでない
        request_body = {
            "url": TEST_URL,
            "memo": "テストメモ",
            "tags": ["tag", "tag"],
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 422

        # タグが10個を超える
        request_body = {
            "url": TEST_URL,
            "memo": "テストメモ",
            "tags": [str(i) for i in range(11)],
        }
        response = client.post("/bookmarks", json=request_body)
        assert response.status_code == 422
