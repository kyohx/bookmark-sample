from datetime import timedelta

from fastapi.testclient import TestClient

from src.libs.enum import AuthorityEnum
from src.main import app
from src.services.authorize import AuthorizeService
from tests.conftest import TEST_PASSWORD, SessionForTest

from ..base import BaseTest


class TestRefreshToken(BaseTest):
    """
    リフレッシュトークンのテストクラス
    """

    def api_path(self) -> str:
        return app.url_path_for("refresh_token")

    def test_refresh_normal(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        正常系:
        リフレッシュトークンでアクセストークン再発行
        """
        # テスト用ユーザの作成
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        # ログインしてリフレッシュトークンを取得
        login_response = client.post(
            app.url_path_for("login"),
            data={"username": "test_user", "password": TEST_PASSWORD},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # リクエストの送信
        response = client.post(self.api_path(), json={"refresh_token": refresh_token})

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "access_token" in response_body
        assert "refresh_token" in response_body
        assert response_body["token_type"] == "bearer"
        assert len(response_body["access_token"]) > 0
        assert len(response_body["refresh_token"]) > 0

    def test_refresh_invalid_token(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        不正なリフレッシュトークン
        """
        response = client.post(self.api_path(), json={"refresh_token": "invalid"})
        assert response.status_code == 401

    def test_refresh_access_token_is_invalid(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        アクセストークンを渡した場合
        """
        # テスト用ユーザの作成
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        # ログインしてアクセストークンを取得
        login_response = client.post(
            app.url_path_for("login"),
            data={"username": "test_user", "password": TEST_PASSWORD},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # アクセストークンをリフレッシュに渡す
        response = client.post(self.api_path(), json={"refresh_token": access_token})
        assert response.status_code == 401

    def test_refresh_disabled_user(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        無効なユーザのリフレッシュ
        """
        # 無効ユーザ作成
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
            disabled=True,
        )

        # リフレッシュトークンを作成
        service = AuthorizeService(session=db_session)
        refresh_token = service.create_refresh_token(
            data={"sub": "test_user"},
            expires_delta=timedelta(days=service.refresh_token_expire_days),
        )

        # リクエストの送信
        response = client.post(self.api_path(), json={"refresh_token": refresh_token})
        assert response.status_code == 401

    def test_refresh_empty_body(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        リクエストボディが空
        """
        response = client.post(self.api_path(), json={})
        assert response.status_code == 422

    def test_refresh_expired_token(
        self,
        client: TestClient,
        db_session: SessionForTest,
    ):
        """
        異常系:
        期限切れのリフレッシュトークン
        """
        # テスト用ユーザの作成
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        # 期限切れトークンを作成
        service = AuthorizeService(session=db_session)
        expired_token = service.create_refresh_token(
            data={"sub": "test_user"},
            expires_delta=timedelta(seconds=-1),
        )

        # リクエストの送信
        response = client.post(self.api_path(), json={"refresh_token": expired_token})
        assert response.status_code == 401
