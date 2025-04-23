from fastapi.testclient import TestClient

from src.libs.util import datetime_to_str
from tests.conftest import TEST_TAG_NAME, SessionForTest

from ..base import BaseTest


class TestGetBookmark(BaseTest):
    """
    ブックマーク取得テストクラス
    """

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
        response = client.get(f"/bookmarks/{db_bookmark.hashed_id}")

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

    def test_get_list_normal(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        通常系:
        ブックマークリスト全件取得
        """
        bookmarks = self.create_bookmarks(db_session, num=2)
        bookmarks_dict = dict([(bookmark.hashed_id, bookmark) for bookmark in bookmarks])

        # リクエストの送信
        response = client.get("/bookmarks")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmarks" in response_body
        res_bookmarks = response_body["bookmarks"]
        assert len(bookmarks) == 2

        for res_bookmark in res_bookmarks:
            assert res_bookmark["hashed_id"] in bookmarks_dict
            db_bookmark = bookmarks_dict[res_bookmark["hashed_id"]]
            assert res_bookmark["url"] == db_bookmark.url
            assert res_bookmark["memo"] == db_bookmark.memo
            assert res_bookmark["hashed_id"] == db_bookmark.hashed_id
            assert "tags" not in res_bookmark
            assert res_bookmark["created_at"] == datetime_to_str(db_bookmark.created_at)
            assert res_bookmark["updated_at"] == datetime_to_str(db_bookmark.updated_at)

    def test_get_list_by_tagname(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        通常系:
        タグ名でブックマークリスト取得
        """
        bookmarks = self.create_bookmarks(db_session, num=2)
        tagname = f"{TEST_TAG_NAME}_1_1"

        # リクエストの送信
        response = client.get(f"/bookmarks?tag={tagname}")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmarks" in response_body
        res_bookmarks = response_body["bookmarks"]
        assert len(res_bookmarks) == 1

        res_bookmark = res_bookmarks[0]
        db_bookmark = bookmarks[0]

        assert res_bookmark["url"] == db_bookmark.url
        assert res_bookmark["memo"] == db_bookmark.memo
        assert res_bookmark["hashed_id"] == db_bookmark.hashed_id
        assert "tags" not in res_bookmark
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
        response = client.get(f"/bookmarks/{hashed_id}")

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
        response = client.get(f"/bookmarks/{hashed_id}")
        assert response.status_code == 422

        # ハッシュIDのフォーマット不正
        hashed_id = "x" * 64
        response = client.get(f"/bookmarks/{hashed_id}")
        assert response.status_code == 422

    def test_get_list_by_tagname_notfound(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        存在しないタグ名でブックマークリスト取得
        """
        # テストデータ作成
        self.create_bookmarks(db_session, num=1)

        # リクエストの送信
        response = client.get("/bookmarks?tag=notfound")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmarks" in response_body
        assert len(response_body["bookmarks"]) == 0

    def test_get_list_by_tagname_invalid(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        タグ名不正
        """
        # タグ名の指定なし
        response = client.get("/bookmarks?tag=")
        assert response.status_code == 422

        # タグ名がユニークでない
        response = client.get("/bookmarks?tag=tag1&tag=tag1")
        assert response.status_code == 422

        # タグ名の長さ不正
        tagname = "x" * 101
        response = client.get(f"/bookmarks?tag={tagname}")
        assert response.status_code == 422

    def test_get_list_pagenation(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        ページネーション
        """
        # テストデータ作成
        self.create_bookmarks(db_session, num=20)

        # リクエストの送信
        response = client.get("/bookmarks?page=2&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmarks" in response_body
        assert len(response_body["bookmarks"]) == 10
        for i, res_bookmark in enumerate(response_body["bookmarks"], start=11):
            assert res_bookmark["memo"] == f"Example{i}"

        # リクエストの送信 (ページ数が大きい)
        response = client.get("/bookmarks?page=3&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmarks" in response_body
        assert len(response_body["bookmarks"]) == 0

    def test_get_list_by_tagname_pagenation(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        タグ名指定でページネーション
        """
        # テストデータ作成
        tags = ["test_tag1", "test_tag2"]
        self.create_bookmarks(db_session, num=20, tag_names=tags)

        # リクエストの送信
        response = client.get(f"/bookmarks?tag={tags[0]}&tag={tags[1]}&page=2&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmarks" in response_body
        assert len(response_body["bookmarks"]) == 10
        for i, res_bookmark in enumerate(response_body["bookmarks"], start=11):
            assert res_bookmark["memo"] == f"Example{i}"

        # リクエストの送信 (ページ数が大きい)
        response = client.get(f"/bookmarks?tag={tags[0]}&tag={tags[1]}&page=3&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmarks" in response_body
        assert len(response_body["bookmarks"]) == 0

    def test_get_list_pagenation_invalid(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        ページネーション指定不正
        """
        # ページ数が0
        response = client.get("/bookmarks?page=0&size=10")
        assert response.status_code == 422

        # ページ数が負数
        response = client.get("/bookmarks?page=-1&size=10")
        assert response.status_code == 422

        # サイズが0
        response = client.get("/bookmarks?page=1&size=0")
        assert response.status_code == 422

        # サイズが負数
        response = client.get("/bookmarks?page=1&size=-1")
        assert response.status_code == 422

        # サイズが100を超える
        response = client.get("/bookmarks?page=1&size=101")
        assert response.status_code == 422
