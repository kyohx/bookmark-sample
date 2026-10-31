from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.libs.util import datetime_to_str
from src.main import app

from ..base import BaseTest
from ..factory import DataFactory
from ..support import TEST_TAG_NAME, SessionForTest


class TestGetBookmarkList(BaseTest):
    """
    ブックマークリスト取得テストクラス
    """

    def api_path(self) -> str:
        return app.url_path_for("get_bookmarks")

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
        bookmarks_dict = {bookmark.hashed_id: bookmark for bookmark in bookmarks}

        # リクエストの送信
        response = client.get(self.api_path())

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

            # タグの検証
            expected_tags = self.get_tags(db_session, db_bookmark)
            assert "tags" in res_bookmark
            assert isinstance(res_bookmark["tags"], list)
            assert len(res_bookmark["tags"]) == len(expected_tags)
            assert set(res_bookmark["tags"]) == {tag.name for tag in expected_tags}
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
        response = client.get(f"{self.api_path()}?tag={tagname}")

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
        # タグの検証
        expected_tags = self.get_tags(db_session, db_bookmark)
        assert "tags" in res_bookmark
        assert isinstance(res_bookmark["tags"], list)
        assert len(res_bookmark["tags"]) == len(expected_tags)
        assert set(res_bookmark["tags"]) == {tag.name for tag in expected_tags}
        assert tagname in res_bookmark["tags"]
        assert res_bookmark["created_at"] == datetime_to_str(db_bookmark.created_at)
        assert res_bookmark["updated_at"] == datetime_to_str(db_bookmark.updated_at)

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
        response = client.get(f"{self.api_path()}?tag=notfound")

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
        response = client.get(f"{self.api_path()}?tag=")
        assert response.status_code == 422

        # タグ名がユニークでない
        response = client.get(f"{self.api_path()}?tag=tag1&tag=tag1")
        assert response.status_code == 422

        # タグ名の長さ不正
        tagname = "x" * 101
        response = client.get(f"{self.api_path()}?tag={tagname}")
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
        bookmarks = self.create_bookmarks(db_session, num=20)
        for bookmark in bookmarks:
            bookmark.created_at = datetime(2025, 1, 1)
        db_session.flush()

        # リクエストの送信
        response = client.get(f"{self.api_path()}?page=2&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmarks" in response_body
        assert len(response_body["bookmarks"]) == 10
        assert [bookmark["memo"] for bookmark in response_body["bookmarks"]] == [
            f"Example{i}" for i in range(10, 0, -1)
        ]

        # リクエストの送信 (ページ数が大きい)
        response = client.get(f"{self.api_path()}?page=3&size=10")

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
        bookmarks = self.create_bookmarks(db_session, num=20, tag_names=tags)
        for bookmark in bookmarks:
            bookmark.created_at = datetime(2025, 1, 1)
        db_session.flush()

        # リクエストの送信
        response = client.get(f"{self.api_path()}?tag={tags[0]}&tag={tags[1]}&page=2&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmarks" in response_body
        assert len(response_body["bookmarks"]) == 10
        assert [bookmark["memo"] for bookmark in response_body["bookmarks"]] == [
            f"Example{i}" for i in range(10, 0, -1)
        ]

        # リクエストの送信 (ページ数が大きい)
        response = client.get(f"{self.api_path()}?tag={tags[0]}&tag={tags[1]}&page=3&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "bookmarks" in response_body
        assert len(response_body["bookmarks"]) == 0

    @pytest.mark.parametrize("tag_filter", [False, True])
    def test_get_list_ordered_by_creation_time_across_pages(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
        tag_filter: bool,
    ):
        """作成日時の降順・同時刻はID降順で、ページ境界でも順序を固定する。"""
        tags = ["test_tag1", "test_tag2"]
        bookmarks = self.create_bookmarks(db_session, num=5, tag_names=tags)
        base_time = datetime(2025, 1, 1, 12)
        # 同じ日付内で時刻を入れ替え、作成日時とIDの順序が異なるデータを用意する。
        for i, seconds in enumerate((1, 3, 2, 3, 3)):
            bookmarks[i].created_at = base_time + timedelta(seconds=seconds)
            bookmarks[i].updated_at = base_time + timedelta(seconds=10 - i)
        if tag_filter:
            excluded = DataFactory(db_session).create_bookmark(
                "https://example.com/excluded", "not matched", ["other"]
            )
            excluded.created_at = base_time + timedelta(seconds=20)
        db_session.flush()
        expected = [bookmarks[i].hashed_id for i in (4, 3, 1, 2, 0)]
        params = {"tag": tags} if tag_filter else {}

        # ページ指定なしの既定取得にも同じ順序を適用する。
        response = client.get(self.api_path(), params=params)
        assert response.status_code == 200
        assert [bookmark["hashed_id"] for bookmark in response.json()["bookmarks"]] == expected

        for page in range(1, 5):
            response = client.get(self.api_path(), params=params | {"page": page, "size": 2})
            assert response.status_code == 200
            assert [bookmark["hashed_id"] for bookmark in response.json()["bookmarks"]] == expected[
                (page - 1) * 2 : page * 2
            ]

        repeated = client.get(self.api_path(), params=params | {"page": 1, "size": 2})
        assert repeated.status_code == 200
        assert [bookmark["hashed_id"] for bookmark in repeated.json()["bookmarks"]] == expected[:2]

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
        response = client.get(f"{self.api_path()}?page=0&size=10")
        assert response.status_code == 422

        # ページ数が負数
        response = client.get(f"{self.api_path()}?page=-1&size=10")
        assert response.status_code == 422

        # サイズが0
        response = client.get(f"{self.api_path()}?page=1&size=0")
        assert response.status_code == 422

        # サイズが負数
        response = client.get(f"{self.api_path()}?page=1&size=-1")
        assert response.status_code == 422

        # サイズが100を超える
        response = client.get(f"{self.api_path()}?page=1&size=101")
        assert response.status_code == 422
