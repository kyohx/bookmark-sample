from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import src.libs.util as util
from src.main import app

from .base import BaseTest
from .support import SessionForTest


class TestDatetimeResponse(BaseTest):
    @pytest.mark.parametrize("resource", ["bookmark", "user"])
    def test_database_datetime_has_explicit_offset(
        self,
        resource: str,
        client: TestClient,
        db_session: SessionForTest,
        mock_get_current_active_user: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = util.get_config().model_copy(update={"database_timezone": "Asia/Tokyo"})
        monkeypatch.setattr(util, "get_config", lambda: config)
        if resource == "bookmark":
            record = self.create_bookmarks(db_session, num=1)[0]
            path = app.url_path_for("get_bookmark", hashed_id=record.hashed_id)
        else:
            record = self.create_user(db_session, "datetime_test")
            path = app.url_path_for("get_user", name=record.name)

        record.created_at = datetime(2025, 1, 1, 0, 0, 1)
        record.updated_at = datetime(2025, 1, 2, 23, 59, 59)
        db_session.flush()
        db_session.expire(record)

        response = client.get(path)
        assert response.status_code == 200
        detail = response.json()[resource]
        assert detail["created_at"] == "2025-01-01T00:00:01+09:00"
        assert detail["updated_at"] == "2025-01-02T23:59:59+09:00"
