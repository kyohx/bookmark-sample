from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import scoped_session, sessionmaker

import src.repositories.base as repository_base
from src.dao.models.base import BaseDao
from src.dao.session import get_session
from src.entities.user import UserEntity
from src.libs.cache import NullCacheRegion
from src.libs.config import get_config
from src.libs.enum import AuthorityEnum
from src.main import app
from src.services.authorize import get_current_active_user, get_current_user_from_token

from .support import SessionForTest

_config = get_config()


@lru_cache
def db_engine() -> Engine:
    """
    テスト用DBエンジン
    """
    db_config = URL.create(
        "mysql+pymysql",
        host=_config.test_database_host,
        port=3306,
        username="root",
        password="root",
        database="test_db",
    )
    return create_engine(db_config, echo=True)


@lru_cache
def get_test_session_factory() -> scoped_session[SessionForTest]:
    return scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=db_engine(),
            class_=SessionForTest,
            expire_on_commit=False,
        )
    )


@pytest.fixture
def db_session() -> SessionForTest:
    """
    テスト用DBセッションメーカー
    """
    return get_test_session_factory()()


@pytest.fixture
def client() -> TestClient:
    """
    テスト用クライアント
    """
    return TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def disable_query_cache_for_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    integration test では rollback でDBだけ巻き戻すため、共有クエリキャッシュを無効化する。
    """
    monkeypatch.setattr(repository_base, "get_query_cache_region", lambda: NullCacheRegion())


@pytest.fixture
def mock_get_current_active_user() -> None:
    """
    ログインユーザー依存処理のモック化
    """

    def get_current_active_user_for_testing() -> UserEntity:
        return UserEntity(
            name="test_user",
            hashed_password="****",
            authority=AuthorityEnum.ADMIN,
            disabled=False,
        )

    app.dependency_overrides[get_current_active_user] = get_current_active_user_for_testing


@pytest.fixture
def mock_get_current_active_not_admin_user() -> None:
    """
    ログインユーザー依存処理のモック化
    (管理者権限ではないユーザーを返す)
    """

    def get_current_active_user_for_testing() -> UserEntity:
        return UserEntity(
            name="test_user",
            hashed_password="****",
            authority=AuthorityEnum.READWRITE,
            disabled=False,
        )

    app.dependency_overrides[get_current_active_user] = get_current_active_user_for_testing


@pytest.fixture
def mock_get_disabled_user_from_token() -> None:
    """
    トークンからのユーザー取得処理のモック化
    (無効化されたユーザーを返す)
    """

    def get_user_from_token_for_testing() -> UserEntity:
        return UserEntity(
            name="test_user",
            hashed_password="****",
            authority=AuthorityEnum.READWRITE,
            disabled=True,
        )

    app.dependency_overrides[get_current_user_from_token] = get_user_from_token_for_testing


@pytest.fixture(scope="function", autouse=True)
def scope_function_test() -> Iterator[None]:
    """
    テスト関数単位の事前事後処理
    """
    session = get_test_session_factory()()

    def get_session_for_testing() -> Iterator[SessionForTest]:
        yield session

    # テスト用依存処理をリセット
    app.dependency_overrides = {}
    # セッション依存処理をテスト用に置き換え
    app.dependency_overrides[get_session] = get_session_for_testing

    yield

    # DBにデータ内容を保存させないためロールバックする
    session.rollback()
    session.close()
    get_test_session_factory().remove()


@pytest.fixture(scope="session", autouse=True)
def truncate_tables() -> Iterator[None]:
    """
    テーブル内容削除
    """
    with db_engine().connect() as con:
        con.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        for table in BaseDao.metadata.sorted_tables:
            con.execute(text(f"TRUNCATE TABLE {table.name};"))
        con.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        con.commit()

    yield
