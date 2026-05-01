from typing import Any

from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from ..log import get_logger

_logger = get_logger()


class SessionResolver:
    def __init__(self, session_attr: str = "session") -> None:
        """
        Session 解決用ヘルパーを初期化する。

        Args:
            session_attr: インスタンスから Session を取得する属性名
        """
        self._session_attr = session_attr

    def resolve(self, args: tuple[object, ...], kwargs: dict[str, object]) -> Session | None:
        """
        関数引数から SQLAlchemy Session を解決する。

        Args:
            args: 位置引数
            kwargs: キーワード引数

        Returns:
            解決した Session。見つからない場合は None
        """
        for value in args:
            if isinstance(value, Session):
                return value

        if args:
            candidate = getattr(args[0], self._session_attr, None)
            if isinstance(candidate, Session):
                return candidate

        for value in kwargs.values():
            if isinstance(value, Session):
                return value

        return None

    def expunge(self, session: Session, result: Any) -> None:
        """
        キャッシュ対象の ORM オブジェクトを Session から切り離す。

        Args:
            session: 対象 Session
            result: expunge 対象の戻り値
        """
        if isinstance(result, list | tuple):
            for value in result:
                self._expunge_one(session, value)
            return

        self._expunge_one(session, result)

    def _expunge_one(self, session: Session, value: Any) -> None:
        """
        単一オブジェクトを Session から切り離す。

        Args:
            session: 対象 Session
            value: expunge 対象の値
        """
        if not hasattr(value, "_sa_instance_state"):
            return

        try:
            session.expunge(value)
        except InvalidRequestError as exc:
            _logger.warning("Failed to expunge cached result: %s", exc)
