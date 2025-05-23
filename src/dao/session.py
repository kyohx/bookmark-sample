from typing import Annotated, Iterator

from fastapi import Depends
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from .engine import Engine

# Sessionの定義
# 同一スレッドでは同じSessionを使い回す
ScopedSession = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=Engine))


def get_session() -> Iterator[Session]:
    """
    セッション取得/制御

    Yields:
        データベースセッション
    """

    session = ScopedSession()
    try:
        with session.begin():
            yield session
    finally:
        ScopedSession.remove()


# 依存定義(コントローラーで使用)
SessionDepend = Annotated[Session, Depends(get_session)]
