from fastapi.testclient import TestClient

from src.dao.models.user import UserDao
from src.entities.user import UserEntity
from src.libs.enum import AuthorityEnum
from src.main import app
from src.services.auth import AuthorizeService, get_current_active_user
from tests.conftest import SessionForTest

from ..base import BaseTest


class TestUpdateUser(BaseTest):
    """
    ブックマーク更新テストクラス
    """

    def test_update_normal(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        ブックマークを1件更新
        """
        self.create_user(db_session, "test1")
        self.create_user(db_session, "test2")

        # リクエストボディの作成
        request_body = {
            "name": "test1_updated",
            "passeword": "password_updated",
            "disabled": True,
            "authority": AuthorityEnum.READ.value,
        }
        # リクエストの送信
        response = client.patch("/users/test1", json=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "updated_user" in response_body
        updated_user = response_body["updated_user"]
        updated_db_user = db_session.query(UserDao).filter_by(name="test1_updated").first()
        assert updated_db_user is not None
        assert updated_user["name"] == updated_db_user.name
        assert updated_user["disabled"] == updated_db_user.disabled
        assert updated_user["authority"] == updated_db_user.authority

    def test_update_name_only(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        ユーザー名のみ更新
        """
        self.create_user(db_session, "test")

        request_body = {"name": "Updated"}
        response = client.patch("/users/test", json=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "updated_user" in response_body
        updated_user = response_body["updated_user"]
        updated_db_user = db_session.query(UserDao).filter_by(name="Updated").first()
        assert updated_db_user is not None
        assert updated_user["name"] == updated_db_user.name
        assert updated_user["disabled"] == updated_db_user.disabled
        assert updated_user["authority"] == updated_db_user.authority

    def test_update_password_only(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        パスワードのみ更新
        """
        self.create_user(db_session, "test")

        request_body = {"password": "UpdatedPassword"}
        response = client.patch("/users/test", json=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "updated_user" in response_body
        updated_user = response_body["updated_user"]
        updated_db_user = db_session.query(UserDao).filter_by(name="test").first()
        assert updated_db_user is not None
        assert updated_user["name"] == updated_db_user.name
        assert AuthorizeService.verify_password(
            request_body["password"], updated_db_user.hashed_password
        )
        assert updated_user["disabled"] == updated_db_user.disabled
        assert updated_user["authority"] == updated_db_user.authority

    def test_update_disabled_only(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        無効フラグのみ更新
        """
        self.create_user(db_session, "test")

        request_body = {"disabled": True}
        response = client.patch("/users/test", json=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "updated_user" in response_body
        updated_user = response_body["updated_user"]
        updated_db_user = db_session.query(UserDao).filter_by(name="test").first()
        assert updated_db_user is not None
        assert updated_user["name"] == updated_db_user.name
        assert updated_user["disabled"] == updated_db_user.disabled
        assert updated_user["authority"] == updated_db_user.authority

    def test_update_authority_only(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        権限のみ更新
        """
        self.create_user(db_session, "test")

        request_body = {"authority": AuthorityEnum.NONE.value}
        response = client.patch("/users/test", json=request_body)

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "updated_user" in response_body
        updated_user = response_body["updated_user"]
        updated_db_user = db_session.query(UserDao).filter_by(name="test").first()
        assert updated_db_user is not None
        assert updated_user["name"] == updated_db_user.name
        assert updated_user["disabled"] == updated_db_user.disabled
        assert updated_user["authority"] == updated_db_user.authority

    def test_update_notfound(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ユーザー名が存在しないユーザー更新
        """
        # テストデータ作成
        self.create_user(db_session, "test")

        # リクエストボディの作成
        request_body = {
            "name": "name_updated",
            "passeword": "password_updated",
            "disabled": True,
            "authority": AuthorityEnum.READ.value,
        }
        # リクエストの送信
        response = client.patch("/users/notfound", json=request_body)

        # レスポンスの検証
        assert response.status_code == 404

    def test_update_invalid_name(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ユーザー名不正
        """
        self.create_user(db_session, "test")

        # ユーザー名が空
        request_body = {
            "name": "",
        }
        response = client.patch("/users/test", json=request_body)
        assert response.status_code == 422

        # ユーザー名の長さが32文字を超える
        request_body = {
            "name": "a" * 33,
        }
        response = client.patch("/users/test", json=request_body)
        assert response.status_code == 422

        # ユーザー名フォーマット不正
        request_body = {
            "name": "test@user",
        }
        response = client.patch("/users/test", json=request_body)
        assert response.status_code == 422

    def test_update_invalid_password(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        パスワード不正
        """
        self.create_user(db_session, "test")

        # パスワードが8文字未満
        request_body = {
            "password": "short",
        }
        response = client.patch("/users/test", json=request_body)
        assert response.status_code == 422

        # パスワードの長さが64文字を超える
        request_body = {
            "password": "a" * 65,
        }
        response = client.patch("/users/test", json=request_body)
        assert response.status_code == 422

    def test_update_invalid_disabled(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        無効フラグ不正
        """
        self.create_user(db_session, "test")

        # 無効フラグがbool型でない
        request_body = {
            "disabled": 100,
        }
        response = client.patch("/users/test", json=request_body)
        assert response.status_code == 422

    def test_update_invalid_authority(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        権限不正
        """
        self.create_user(db_session, "test")

        # 権限が存在しない値
        request_body = {
            "authority": 1000,
        }
        response = client.patch("/users/test", json=request_body)
        assert response.status_code == 422

    def test_update_own_attribute(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        ログインユーザ自身の属性を更新
        """
        self.create_user(db_session, "test_user", authority=AuthorityEnum.ADMIN)

        # ログインユーザーの名前更新
        request_body = {
            "name": "name_updated",
        }
        response = client.patch("/users/test_user", json=request_body)
        assert response.status_code == 400

        # ログインユーザーのパスワード更新
        request_body = {
            "password": "password_updated",
        }
        response = client.patch("/users/test_user", json=request_body)
        assert response.status_code == 200  # パスワード更新は成功する

        # ログインユーザーの無効フラグ更新
        request_body = {
            "disabled": True,
        }
        response = client.patch("/users/test_user", json=request_body)
        assert response.status_code == 400

        # ログインユーザーの権限更新
        request_body = {
            "authority": AuthorityEnum.READ.value,
        }
        response = client.patch("/users/test_user", json=request_body)
        assert response.status_code == 400

    def test_update_by_not_admin_user(self, client: TestClient, db_session: SessionForTest):
        """
        異常系:
        権限がないユーザーが他のユーザーを更新
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

        # リクエストボディの作成
        request_body = {
            "name": "name_updated",
            "passeword": "password_updated",
            "disabled": True,
            "authority": AuthorityEnum.READ.value,
        }
        # リクエストの送信
        response = client.patch("/users/test", json=request_body)

        # レスポンスの検証
        assert response.status_code == 403
