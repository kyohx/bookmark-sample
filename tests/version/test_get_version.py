from fastapi.testclient import TestClient

from src.libs.version import APP_VERSION
from tests.conftest import SessionForTest

from ..base import BaseTest


class TestGetVersion(BaseTest):
    """
    バージョン取得テストクラス
    """

    def test_get_version(self, client: TestClient, db_session: SessionForTest):
        """
        正常系:
        バージョン取得
        """
        # リクエストの送信
        response = client.get("/version")

        # レスポンスの検証
        assert response.status_code == 200
        response_body = response.json()
        assert "version" in response_body
        assert response_body["version"] == APP_VERSION
