from fastapi.testclient import TestClient

from src.libs.enum import AuthorityEnum
from tests.conftest import SessionForTest

from ..base import BaseTest


class TestMe(BaseTest):
    def test_get_login_user_normal(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        ログインユーザー取得
        """
        # リクエストの送信
        response = client.get("/me")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert response_body["name"] == "test_user"
        assert response_body["authority"] == AuthorityEnum.ADMIN.value

    def test_not_authenticated(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        認証されていない
        """
        # リクエストの送信
        response = client.get("/me")

        # レスポンスの検証
        print(response.json())
        assert response.status_code == 401
