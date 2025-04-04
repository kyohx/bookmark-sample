import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from src.dao.models.base import BaseDao
from src.dao.session import get_session
from src.entities.user import User
from src.libs.auth import get_current_active_user
from src.libs.enum import AuthorityEnum
from src.main import app
from src.libs.config import get_config

_config = get_config()

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
        host=_config.test_database_host,
        port=3306,
        username="root",
        password="root",
        database="test_db",
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

    def get_session_for_testing():
        yield session

    def get_current_active_user_for_testing():
        return User(
            name="test_user",
            hashed_password="****",
            authority=AuthorityEnum.READWRITE,
            disabled=False,
        )

    # 依存処理をテスト用に置き換え
    app.dependency_overrides[get_session] = get_session_for_testing
    app.dependency_overrides[get_current_active_user] = get_current_active_user_for_testing

    yield  # テスト関数実行

    # DBにデータ内容を保存させないためロールバックする
    session.rollback()


@pytest.fixture(scope="session", autouse=True)
def truncate_tables():
    """
    テーブル内容削除
    """
    with engine.connect() as con:
        con.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        for table in BaseDao.metadata.sorted_tables:
            con.execute(text(f"TRUNCATE TABLE {table.name};"))
        con.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        con.commit()
