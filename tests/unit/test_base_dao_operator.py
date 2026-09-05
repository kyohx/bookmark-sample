from collections.abc import Iterator

import pytest
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.dao.models.base import BaseDao, TimeStampColumnMixin
from src.dao.operators.base import BaseDaoOperator


class _DaoWithCreatedAt(BaseDao, TimeStampColumnMixin):
    __tablename__ = "test_with_created_at"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class _DaoWithoutCreatedAt(BaseDao):
    __tablename__ = "test_without_created_at"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class _OpWithTimestamp(BaseDaoOperator[_DaoWithCreatedAt]):
    MAIN_DAO = _DaoWithCreatedAt


class _OpWithoutTimestamp(BaseDaoOperator[_DaoWithoutCreatedAt]):
    MAIN_DAO = _DaoWithoutCreatedAt


@pytest.fixture
def session(sqlite_session_factory) -> Iterator[Session]:
    # テスト用の in-memory SQLite セッションを用意
    with sqlite_session_factory(BaseDao.metadata) as db_session:
        yield db_session


def test_save_adds_object_with_created_at_none(session: Session) -> None:
    """created_at 属性を持ち (None の) DAO は session.add されることを検証"""
    op = _OpWithTimestamp(session)
    dao = _DaoWithCreatedAt()

    # 初期状態では persisted でない
    assert getattr(dao, "id", None) is None

    op.save(dao)

    # flush() により DB に登録され id が付与されているはず
    assert session.query(_DaoWithCreatedAt).count() == 1


def test_save_does_not_add_object_without_created_at(session: Session) -> None:
    """created_at 属性を持たない DAO は session.add されず、DB に挿入されないことを検証"""
    op = _OpWithoutTimestamp(session)
    dao = _DaoWithoutCreatedAt()

    op.save(dao)

    # created_at を持たないため追加されておらず、テーブルは空のまま
    assert session.query(_DaoWithoutCreatedAt).count() == 0
