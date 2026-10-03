import re
from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from src.libs.enum import AuthorityEnum
from src.main import app
from src.services.authorize import AuthorizeService, RefreshTokenPayload

from ..base import BaseTest
from ..support import TEST_PASSWORD, SessionForTest


class TestSessions(BaseTest):
    def _create_user(self, db_session: SessionForTest) -> str:
        name = f"session_{uuid4().hex[:16]}"
        self.create_user(db_session, name=name, authority=AuthorityEnum.READWRITE)
        return name

    def _login(self, client: TestClient, name: str, agent: str = "test client") -> str:
        response = client.post(
            app.url_path_for("login"),
            data={"username": name, "password": TEST_PASSWORD},
            headers={"user-agent": agent},
        )
        assert response.status_code == 200
        return response.json()["refresh_token"]

    def _family(self, db_session: SessionForTest, token: str) -> str:
        return AuthorizeService(db_session)._decode_token(token, RefreshTokenPayload).fam

    def test_list_and_revoke_one_session(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ) -> None:
        name = self._create_user(db_session)
        first_token = self._login(client, name, "first device")
        second_token = self._login(client, name, "second device")
        first_family = self._family(db_session, first_token)
        second_family = self._family(db_session, second_token)

        list_path = app.url_path_for("get_user_sessions", name=name)
        response = client.get(list_path)
        assert response.status_code == 200
        sessions = {session["id"]: session for session in response.json()["sessions"]}
        assert set(sessions) == {first_family, second_family}
        assert sessions[first_family]["user_agent"] == "first device"
        assert sessions[first_family]["revoked"] is False
        for field in ("created_at", "last_used_at", "expires_at"):
            assert re.fullmatch(
                r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", sessions[first_family][field]
            )
        assert "refresh_token" not in sessions[first_family]

        revoke_path = app.url_path_for("revoke_user_session", name=name, session_id=first_family)
        assert client.delete(revoke_path).status_code == 204
        assert client.delete(revoke_path).status_code == 204
        sessions = {session["id"]: session for session in client.get(list_path).json()["sessions"]}
        assert sessions[first_family]["revoked"] is True
        assert sessions[second_family]["revoked"] is False

        refresh_path = app.url_path_for("refresh_token")
        assert client.post(refresh_path, json={"refresh_token": first_token}).status_code == 401
        assert client.post(refresh_path, json={"refresh_token": second_token}).status_code == 200

    def test_refresh_updates_session(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ) -> None:
        name = self._create_user(db_session)
        token = self._login(client, name)
        family = self._family(db_session, token)
        response = client.post(app.url_path_for("refresh_token"), json={"refresh_token": token})
        assert response.status_code == 200
        assert self._family(db_session, response.json()["refresh_token"]) == family
        sessions = client.get(app.url_path_for("get_user_sessions", name=name)).json()["sessions"]
        assert len(sessions) == 1
        assert sessions[0]["id"] == family
        assert sessions[0]["last_used_at"] >= sessions[0]["created_at"]

    def test_reused_refresh_token_marks_session_revoked(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ) -> None:
        name = self._create_user(db_session)
        token = self._login(client, name)
        refresh_path = app.url_path_for("refresh_token")
        assert client.post(refresh_path, json={"refresh_token": token}).status_code == 200
        assert client.post(refresh_path, json={"refresh_token": token}).status_code == 401
        sessions = client.get(app.url_path_for("get_user_sessions", name=name)).json()["sessions"]
        assert len(sessions) == 1
        assert sessions[0]["revoked"] is True

    def test_preexisting_token_is_listed_after_refresh(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ) -> None:
        name = self._create_user(db_session)
        service = AuthorizeService(db_session)
        token = service.create_refresh_token(
            data={"sub": name, "jti": uuid4().hex, "fam": uuid4().hex},
            expires_delta=timedelta(days=1),
        )
        path = app.url_path_for("get_user_sessions", name=name)
        assert client.get(path).json()["sessions"] == []
        assert (
            client.post(
                app.url_path_for("refresh_token"), json={"refresh_token": token}
            ).status_code
            == 200
        )
        sessions = client.get(path).json()["sessions"]
        assert len(sessions) == 1
        assert sessions[0]["user_agent"] is None

    def test_missing_session_and_user(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ) -> None:
        name = self._create_user(db_session)
        path = app.url_path_for("revoke_user_session", name=name, session_id="missing")
        assert client.delete(path).status_code == 404
        missing_user_path = app.url_path_for("get_user_sessions", name="unknown_user")
        assert client.get(missing_user_path).status_code == 404

    def test_session_cannot_be_revoked_under_another_user(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ) -> None:
        owner = self._create_user(db_session)
        other = self._create_user(db_session)
        token = self._login(client, owner)
        family = self._family(db_session, token)
        wrong_path = app.url_path_for("revoke_user_session", name=other, session_id=family)
        assert client.delete(wrong_path).status_code == 404
        assert (
            client.post(
                app.url_path_for("refresh_token"), json={"refresh_token": token}
            ).status_code
            == 200
        )

    def test_non_admin_cannot_manage_sessions(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_not_admin_user: None,
    ) -> None:
        name = self._create_user(db_session)
        assert client.get(app.url_path_for("get_user_sessions", name=name)).status_code == 403
        path = app.url_path_for("revoke_user_session", name=name, session_id="unknown")
        assert client.delete(path).status_code == 403

    def test_blacklist_routes_are_removed(self, client: TestClient) -> None:
        assert client.post("/auth/blacklist/family", json={}).status_code == 404
        assert client.delete("/auth/blacklist/family/user/family").status_code == 404
        assert client.post("/auth/blacklist/jti", json={}).status_code == 404
        assert client.delete("/auth/blacklist/jti/jti").status_code == 404
