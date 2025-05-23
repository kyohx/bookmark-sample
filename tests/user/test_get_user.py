from fastapi.testclient import TestClient

from src.entities.user import UserEntity
from src.libs.enum import AuthorityEnum
from src.main import app
from src.services.authorize import get_current_active_user
from tests.conftest import SessionForTest

from ..base import BaseTest


class TestGetUser(BaseTest):
    """
    ユーザー取得テストクラス
    """

    def api_path(self, name: str) -> str:
        return app.url_path_for("get_user", name=name)

    def test_get_one_normal(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        ユーザーを1つ取得
        """
        db_user = self.create_user(db_session, "test")

        # リクエストの送信
        response = client.get(self.api_path(db_user.name))

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "user" in response_body
        res_user = response_body["user"]
        assert res_user["name"] == db_user.name
        assert res_user["disabled"] == db_user.disabled
        assert res_user["authority"] == db_user.authority

    def test_get_one_notfound(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        ユーザー名が存在しないユーザー取得
        """
        # テストデータ作成
        self.create_user(db_session, "test")

        # リクエストの送信
        response = client.get(self.api_path("notfound"))

        # レスポンスの検証
        assert response.status_code == 404

    def test_get_invalid_name(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        ユーザー名不正
        """
        # ユーザー名の長さが32文字を超える
        name = "a" * 33
        response = client.get(self.api_path(name))
        assert response.status_code == 422

        # ユーザー名のフォーマット不正
        name = "ユーザー"
        response = client.get(self.api_path(name))
        assert response.status_code == 422

    def test_get_one_by_not_admin_user(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
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
        response = client.get(self.api_path("test"))

        # レスポンスの検証
        assert response.status_code == 403
