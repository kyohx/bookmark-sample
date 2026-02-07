from datetime import timedelta

import pytest
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
            data={"sub": "test_user", "jti": "jti-test", "fam": "fam-test"},
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
            data={"sub": "test_user", "jti": "jti-expired", "fam": "fam-expired"},
            expires_delta=timedelta(seconds=-1),
        )

        # リクエストの送信
        response = client.post(self.api_path(), json={"refresh_token": expired_token})
        assert response.status_code == 401

    def test_refresh_reuse_denies_family_and_jti(
        self,
        db_session: SessionForTest,
    ):
        """
        異常系:
        リフレッシュトークンの再利用検知時にfamily/jtiが両方denyされる
        """
        # テスト用ユーザの作成
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        service = AuthorizeService(session=db_session)
        family = "family-1"
        refresh_jti = "jti-1"
        refresh_token = service.create_refresh_token(
            data={"sub": "test_user", "jti": refresh_jti, "fam": family},
            expires_delta=timedelta(days=1),
        )

        class StubBlacklist:
            def __init__(self) -> None:
                self.denied_family: tuple[str, str, int, str] | None = None
                self.denied_jti: tuple[str, int, str] | None = None

            def is_jti_denied(self, jti: str) -> bool:
                return False

            def is_family_denied(self, user: str, family_id: str) -> bool:
                return False

            def get_current_jti(self, user: str, family_id: str) -> str:
                return "other-jti"

            def deny_family(self, user: str, family_id: str, ttl: int, reason: str) -> None:
                self.denied_family = (user, family_id, ttl, reason)

            def deny_jti(self, jti: str, ttl: int, reason: str) -> None:
                self.denied_jti = (jti, ttl, reason)

        stub = StubBlacklist()
        service.blacklist_service = stub

        with pytest.raises(AuthorizeService.Error):
            service.refresh(refresh_token)

        assert stub.denied_family is not None
        assert stub.denied_jti is not None
        assert stub.denied_family[0] == "test_user"
        assert stub.denied_family[1] == family
        assert stub.denied_family[2] >= 0
        assert stub.denied_family[3] == "reuse detected"
        assert stub.denied_jti[0] == refresh_jti
        assert stub.denied_jti[1] >= 0
        assert stub.denied_jti[2] == "reuse detected"
