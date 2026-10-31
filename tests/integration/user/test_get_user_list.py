from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from src.dao.models.user import UserDao
from src.libs.util import datetime_to_str
from src.main import app

from ..base import BaseTest
from ..support import SessionForTest


class TestGetUserList(BaseTest):
    """
    ユーザーリスト取得テストクラス
    """

    def api_path(self) -> str:
        return app.url_path_for("get_users")

    def test_get_list_normal(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        通常系:
        ユーザーリスト全件取得
        """
        self.create_user(db_session, "test1")
        self.create_user(db_session, "test2")
        users = db_session.query(UserDao).all()
        users_dict = {user.name: user for user in users}

        # リクエストの送信
        response = client.get(self.api_path())

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "users" in response_body
        res_users = response_body["users"]
        assert len(users) == 2

        for res_user in res_users:
            assert res_user["name"] in users_dict
            db_user = users_dict[res_user["name"]]
            assert res_user["disabled"] == db_user.disabled
            assert res_user["authority"] == db_user.authority
            assert res_user["created_at"] == datetime_to_str(db_user.created_at)
            assert res_user["updated_at"] == datetime_to_str(db_user.updated_at)

    def test_get_list_by_not_admin_user(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_not_admin_user: None,
    ):
        """
        異常系:
        権限がないユーザーがユーザー情報リストを取得
        """
        self.create_user(db_session, "test")

        # リクエストの送信
        response = client.get(self.api_path())

        # レスポンスの検証
        assert response.status_code == 403

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
        for i in range(20):
            self.create_user(db_session, f"test{i + 1}")
        for user in db_session.query(UserDao).all():
            user.created_at = datetime(2025, 1, 1)
        db_session.flush()

        # リクエストの送信
        response = client.get(f"{self.api_path()}?page=2&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "users" in response_body
        assert len(response_body["users"]) == 10
        assert [user["name"] for user in response_body["users"]] == [
            f"test{i}" for i in range(10, 0, -1)
        ]

        # リクエストの送信 (ページ数が大きい)
        response = client.get(f"{self.api_path()}?page=3&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "users" in response_body
        assert len(response_body["users"]) == 0

    def test_get_list_ordered_by_creation_time_across_pages(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """作成日時の降順・同時刻はID降順で、ページ境界でも順序を固定する。"""
        for i in range(5):
            self.create_user(db_session, f"test{i}")
        users = db_session.query(UserDao).order_by(UserDao.id).all()
        base_time = datetime(2025, 1, 1, 12)
        for i, seconds in enumerate((1, 3, 2, 3, 3)):
            users[i].created_at = base_time + timedelta(seconds=seconds)
            users[i].updated_at = base_time + timedelta(seconds=10 - i)
        db_session.flush()
        expected = [users[i].name for i in (4, 3, 1, 2, 0)]

        response = client.get(self.api_path())
        assert response.status_code == 200
        assert [user["name"] for user in response.json()["users"]] == expected

        for page in range(1, 5):
            response = client.get(self.api_path(), params={"page": page, "size": 2})
            assert response.status_code == 200
            assert [user["name"] for user in response.json()["users"]] == expected[
                (page - 1) * 2 : page * 2
            ]

        repeated = client.get(self.api_path(), params={"page": 1, "size": 2})
        assert repeated.status_code == 200
        assert [user["name"] for user in repeated.json()["users"]] == expected[:2]

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
