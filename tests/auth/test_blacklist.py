from fastapi.testclient import TestClient

from src.libs.enum import AuthorityEnum
from src.main import app
from src.services.authorize import AuthorizeService, TokenType
from tests.conftest import TEST_PASSWORD, SessionForTest

from ..base import BaseTest


class TestBlacklist(BaseTest):
    """
    ブラックリストAPIのテストクラス
    """

    def _get_refresh_payload(self, db_session: SessionForTest, refresh_token: str) -> dict:
        service = AuthorizeService(session=db_session)
        return service._decode_token(refresh_token, expected_type=TokenType.REFRESH)

    def test_blacklist_add_jti_admin(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        jtiでブラックリスト追加
        """
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        login_response = client.post(
            app.url_path_for("login"),
            data={"username": "test_user", "password": TEST_PASSWORD},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        payload = self._get_refresh_payload(db_session, refresh_token)

        response = client.post(
            app.url_path_for("add_blacklist_jti"),
            json={"jti": payload["jti"], "reason": "security"},
        )
        assert response.status_code == 204

        refresh_response = client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 401

    def test_blacklist_add_user_family_admin(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        user+familyでブラックリスト追加
        """
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        login_response = client.post(
            app.url_path_for("login"),
            data={"username": "test_user", "password": TEST_PASSWORD},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        payload = self._get_refresh_payload(db_session, refresh_token)

        response = client.post(
            app.url_path_for("add_blacklist_family"),
            json={
                "user": payload["sub"],
                "family": payload["fam"],
                "reason": "incident",
            },
        )
        assert response.status_code == 204

        refresh_response = client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 401

    def test_blacklist_delete_jti_admin(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        jtiのブラックリスト削除
        """
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        login_response = client.post(
            app.url_path_for("login"),
            data={"username": "test_user", "password": TEST_PASSWORD},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        payload = self._get_refresh_payload(db_session, refresh_token)

        client.post(
            app.url_path_for("add_blacklist_jti"),
            json={"jti": payload["jti"], "reason": "test"},
        )

        response = client.request(
            "DELETE",
            app.url_path_for("delete_blacklist_jti", jti=payload["jti"]),
        )
        assert response.status_code == 204

        refresh_response = client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200

    def test_blacklist_delete_user_family_admin(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        user+familyのブラックリスト削除
        """
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        login_response = client.post(
            app.url_path_for("login"),
            data={"username": "test_user", "password": TEST_PASSWORD},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        payload = self._get_refresh_payload(db_session, refresh_token)

        client.post(
            app.url_path_for("add_blacklist_family"),
            json={
                "user": payload["sub"],
                "family": payload["fam"],
                "reason": "test",
            },
        )

        response = client.request(
            "DELETE",
            app.url_path_for(
                "delete_blacklist_family",
                user=payload["sub"],
                family=payload["fam"],
            ),
        )
        assert response.status_code == 204

        refresh_response = client.post(
            app.url_path_for("refresh_token"),
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200

    def test_blacklist_delete_jti_not_found(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        存在しないjtiの削除は404
        """
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        login_response = client.post(
            app.url_path_for("login"),
            data={"username": "test_user", "password": TEST_PASSWORD},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        payload = self._get_refresh_payload(db_session, refresh_token)

        response = client.request(
            "DELETE",
            app.url_path_for("delete_blacklist_jti", jti=payload["jti"]),
        )
        assert response.status_code == 404

    def test_blacklist_delete_user_family_not_found(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        存在しないuser+familyの削除は404
        """
        self.create_user(
            db_session,
            name="test_user",
            authority=AuthorityEnum.READWRITE,
        )

        login_response = client.post(
            app.url_path_for("login"),
            data={"username": "test_user", "password": TEST_PASSWORD},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        payload = self._get_refresh_payload(db_session, refresh_token)

        response = client.request(
            "DELETE",
            app.url_path_for(
                "delete_blacklist_family",
                user=payload["sub"],
                family=payload["fam"],
            ),
        )
        assert response.status_code == 404

    def test_blacklist_add_jti_validation_error(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        jtiが不正な場合は422
        """
        response = client.post(
            app.url_path_for("add_blacklist_jti"),
            json={"jti": "", "reason": "test"},
        )
        assert response.status_code == 422

    def test_blacklist_add_family_validation_error(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        user/familyが不正な場合は422
        """
        response = client.post(
            app.url_path_for("add_blacklist_family"),
            json={
                "user": "bad-user",
                "family": "",
                "reason": "test",
            },
        )
        assert response.status_code == 422

    def test_blacklist_delete_jti_validation_error(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        jtiが不正な場合は422
        """
        invalid_jti = "a" * 129
        response = client.request(
            "DELETE",
            app.url_path_for("delete_blacklist_jti", jti=invalid_jti),
        )
        assert response.status_code == 422

    def test_blacklist_delete_family_validation_error(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        user/familyが不正な場合は422
        """
        invalid_family = "a" * 129
        response = client.request(
            "DELETE",
            app.url_path_for(
                "delete_blacklist_family",
                user="bad-user",
                family=invalid_family,
            ),
        )
        assert response.status_code == 422

    def test_blacklist_non_admin_forbidden(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_not_admin_user: None,
    ):
        """
        異常系:
        非管理者は操作できない
        """
        response = client.post(
            app.url_path_for("add_blacklist_jti"),
            json={"jti": "abcd"},
        )
        assert response.status_code == 403
