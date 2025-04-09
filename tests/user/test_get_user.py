from fastapi.testclient import TestClient

from src.dao.models.user import UserDao
from src.entities.user import UserEntity
from src.libs.enum import AuthorityEnum
from src.main import app
from src.services.auth import get_current_active_user
from tests.conftest import SessionForTest

from ..base import BaseTest


class TestGetUser(BaseTest):
    """
    ユーザー取得テストクラス
    """

    def test_get_one_normal(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        ユーザーを1つ取得
        """
        db_user = self.create_user(db_session, "test")

        # リクエストの送信
        response = client.get(f"/users/{db_user.name}")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "user" in response_body
        res_user = response_body["user"]
        assert res_user["name"] == db_user.name
        assert res_user["disabled"] == db_user.disabled
        assert res_user["authority"] == db_user.authority

    def test_get_list_normal(self, client: TestClient, db_session: SessionForTest):
        """
        通常系:
        ユーザーリスト全件取得
        """
        self.create_user(db_session, "test1")
        self.create_user(db_session, "test2")
        users = db_session.query(UserDao).all()
        users_dict = dict([(user.name, user) for user in users])

        # リクエストの送信
        response = client.get("/users")

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

    def test_get_one_notfound(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ユーザー名が存在しないユーザー取得
        """
        # テストデータ作成
        self.create_user(db_session, "test")

        # リクエストの送信
        response = client.get("/users/notfound")

        # レスポンスの検証
        assert response.status_code == 404

    def test_get_invalid_name(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ユーザー名不正
        """
        # ユーザー名の長さが32文字を超える
        name = "a" * 33
        response = client.get(f"/users/{name}")
        assert response.status_code == 422

        # ユーザー名のフォーマット不正
        name = "ユーザー"
        response = client.get(f"/users/{name}")
        assert response.status_code == 422

    def test_get_one_by_not_admin_user(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        権限がないユーザーがユーザー情報を1つ取得
        """

        def get_current_active_user_for_not_admin_testing():
            return UserEntity(
                name="test_user",
                hashed_password="****",
                authority=AuthorityEnum.READWRITE,
                disabled=False,
            )

        app.dependency_overrides[get_current_active_user] = (
            get_current_active_user_for_not_admin_testing
        )

        self.create_user(db_session, "test")

        # リクエストの送信
        response = client.get("/users/test")

        # レスポンスの検証
        assert response.status_code == 403

    def test_get_list_by_not_admin_user(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        権限がないユーザーがユーザー情報リストを取得
        """

        def get_current_active_user_for_not_admin_testing():
            return UserEntity(
                name="test_user",
                hashed_password="****",
                authority=AuthorityEnum.READWRITE,
                disabled=False,
            )

        app.dependency_overrides[get_current_active_user] = (
            get_current_active_user_for_not_admin_testing
        )

        self.create_user(db_session, "test")

        # リクエストの送信
        response = client.get("/users")

        # レスポンスの検証
        assert response.status_code == 403
