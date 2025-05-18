from fastapi.testclient import TestClient

from src.dao.models.user import UserDao
from src.libs.enum import AuthorityEnum
from src.main import app
from src.services.authorize import AuthorizeService
from tests.conftest import SessionForTest

from ..base import BaseTest


class TestAddUser(BaseTest):
    """
    ユーザー追加のテストクラス
    """

    def api_path(self) -> str:
        return app.url_path_for("add_user")

    def test_add_normal(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        正常系:
        ユーザーを1つ追加
        """
        assert db_session.query(UserDao).count() == 0

        # リクエストボディの作成
        request_body = {
            "name": "test",
            "password": "password",
            "authority": AuthorityEnum.READWRITE.value,
        }

        # リクエストの送信
        response = client.post(self.api_path(), json=request_body)

        # レスポンスの検証
        assert response.status_code == 200

        # データベースの検証
        users = db_session.query(UserDao).all()
        assert len(users) == 1
        user = users[0]
        assert user.name == request_body["name"]
        assert AuthorizeService.verify_password(request_body["password"], user.hashed_password)
        assert user.disabled is False
        assert user.authority == request_body["authority"]

    def test_add_duplicate(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        ユーザー重複追加
        """
        ## 追加
        request_body = {
            "name": "test",
            "password": "password",
            "authority": AuthorityEnum.READWRITE.value,
        }
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 200

        ## 同じユーザー情報を追加
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 409

    def test_add_invalid_name(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        ユーザー名不正
        """
        # ユーザー名の指定なし
        request_body = {
            "password": "password",
            "authority": AuthorityEnum.READWRITE.value,
        }
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 422

        # 不正なユーザー名
        request_body = {
            "name": "testテスト",
            "password": "password",
            "authority": AuthorityEnum.READWRITE.value,
        }
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 422

        # ユーザー名の長さが32文字を超える
        request_body = {
            "name": "a" * 33,
            "password": "password",
            "authority": AuthorityEnum.READWRITE.value,
        }
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 422

        # ユーザー名が空
        request_body = {
            "name": "",
            "password": "password",
            "authority": AuthorityEnum.READWRITE.value,
        }
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 422

    def test_add_invalid_password(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        パスワード不正
        """
        # パスワード指定なし
        request_body = {
            "name": "test",
            "authority": AuthorityEnum.READWRITE.value,
        }
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 422

        # パスワードの長さが64文字を超える
        request_body = {
            "name": "test",
            "password": "p" * 65,
            "authority": AuthorityEnum.READWRITE.value,
        }
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 422

        # パスワードの長さが8文字未満
        request_body = {
            "name": "test",
            "password": "p" * 7,
            "authority": AuthorityEnum.READWRITE.value,
        }
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 422

    def test_add_invalid_authority(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
    ):
        """
        異常系:
        権限不正
        """
        # 権限指定なし
        request_body = {
            "name": "test",
            "password": "password",
        }
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 422

        # 権限の値が不正
        request_body = {
            "name": "test",
            "password": "password",
            "authority": 7,
        }
        response = client.post(self.api_path(), json=request_body)
        assert response.status_code == 422

    def test_add_by_not_admin_user(
        self,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_not_admin_user: None,
    ):
        """
        異常系:
        権限がないユーザーがユーザー追加
        """
        request_body = {
            "name": "test",
            "password": "password",
            "authority": AuthorityEnum.READWRITE.value,
        }

        # リクエストの送信
        response = client.post(self.api_path(), json=request_body)

        # レスポンスの検証
        assert response.status_code == 403
