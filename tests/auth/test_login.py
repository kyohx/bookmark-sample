from fastapi.testclient import TestClient

from src.libs.enum import AuthorityEnum
from src.main import app
from tests.conftest import TEST_PASSWORD, SessionForTest

from ..base import BaseTest


class TestLogin(BaseTest):
    """
    ログイン機能のテストクラス
    """

    def api_path(self) -> str:
        return app.url_path_for("login")

    def test_login_normal(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        正常系:
        ログイン
        """
        # テスト用ユーザの作成
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        # リクエストボディの作成
        request_body = {
            "username": "test_user",
            "password": TEST_PASSWORD,
        }

        # リクエストの送信
        response = client.post(self.api_path(), data=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "access_token" in response_body
        assert "refresh_token" in response_body
        assert "token_type" in response_body
        assert response_body["token_type"] == "bearer"
        assert len(response_body["access_token"]) > 0
        assert len(response_body["refresh_token"]) > 0

    def test_login_invalid_user(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        存在しないユーザでログイン
        """
        # リクエストボディの作成
        request_body = {
            "username": "test_user",
            "password": TEST_PASSWORD,
        }

        # リクエストの送信
        response = client.post(self.api_path(), data=request_body)

        # レスポンスの検証
        assert response.status_code == 401

    def test_login_invalid_password(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        パスワード不一致
        """
        # テスト用ユーザの作成
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        # リクエストボディの作成
        request_body = {
            "username": "test_user",
            "password": "invalid_password",
        }

        # リクエストの送信
        response = client.post(self.api_path(), data=request_body)

        # レスポンスの検証
        assert response.status_code == 401

    def test_login_disabled_user(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        無効なユーザでログイン
        """
        # テスト用ユーザの作成
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
            disabled=True,
        )

        # リクエストボディの作成
        request_body = {
            "username": "test_user",
            "password": TEST_PASSWORD,
        }

        # リクエストの送信
        response = client.post(self.api_path(), data=request_body)

        # レスポンスの検証
        assert response.status_code == 401

    def test_login_empty_username(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        ユーザ名が空
        """
        # リクエストボディの作成
        request_body = {
            "username": "",
            "password": TEST_PASSWORD,
        }

        # リクエストの送信
        response = client.post(self.api_path(), data=request_body)

        # レスポンスの検証
        assert response.status_code == 422

    def test_login_empty_password(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        パスワードが空
        """
        # リクエストボディの作成
        request_body = {
            "username": "test_user",
            "password": "",
        }

        # リクエストの送信
        response = client.post(self.api_path(), data=request_body)

        # レスポンスの検証
        assert response.status_code == 422
