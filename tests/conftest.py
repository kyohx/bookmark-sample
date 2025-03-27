import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from src.dao.session import get_session
from src.main import app

TEST_URL = "https://exsample.com/test"
TEST_TAG_NAME = "test_tag"
TEST_TAGS = ["test_tag1", "test_tag2"]


class SessionForTest(Session):
    """
    テスト用セッション
    """

    def commit(self):
        # 実際にコミットしないようにする
        self.flush()
        self.expire_all()


def db_engine():
    """
    テスト用DBエンジン
    """
    config = URL.create(
        "mysql+pymysql",
        host=os.environ.get("TEST_DB_HOST", "test_db"),
        port=int(os.environ.get("TEST_DB_PORT", "3306")),
        username="root",
        password="root",
        database="app",
    )

    engine = create_engine(config, echo=True)
    return engine


engine = db_engine()

get_test_session = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=SessionForTest,
        expire_on_commit=False,
    )
)


@pytest.fixture(scope="function")
def db_session() -> SessionForTest:
    """
    テスト用DBセッションメーカー
    """
    return get_test_session()


@pytest.fixture(scope="module")
def client():
    """
    テスト用クライアント
    """
    return TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def scope_funtion_test():
    """
    テスト関数単位の事前事後処理
    """
    session = get_test_session()

    def get_session_for_testing_app():
        yield session

    # APIで使用しているセッション取得処理をテスト用に置き換え
    app.dependency_overrides[get_session] = get_session_for_testing_app

    yield  # テスト関数実行

    # DBにデータ内容を保存させないためロールバックする
    session.rollback()
