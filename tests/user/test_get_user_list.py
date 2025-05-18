from fastapi.testclient import TestClient

from src.dao.models.user import UserDao
from src.main import app
from tests.conftest import SessionForTest

from ..base import BaseTest


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
        users_dict = dict([(user.name, user) for user in users])

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

        # リクエストの送信
        response = client.get(f"{self.api_path()}?page=2&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "users" in response_body
        assert len(response_body["users"]) == 10
        for i, res_user in enumerate(response_body["users"], start=11):
            assert res_user["name"] == f"test{i}"

        # リクエストの送信 (ページ数が大きい)
        response = client.get(f"{self.api_path()}?page=3&size=10")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "users" in response_body
        assert len(response_body["users"]) == 0

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
