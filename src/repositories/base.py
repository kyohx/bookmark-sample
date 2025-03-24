from sqlalchemy.orm.session import Session

from ..dao.session import ScopedSession


class RepositoryError(Exception):
    pass


class BaseRepository:
    """
    レポジトリベースクラス
    外部データ(DB等)に対し操作する
    """

    class NotFoundError(RepositoryError):
        pass

    def __init__(self, session: Session | None = None) -> None:
        """
        初期化

        :param session: セッション
        """
        self.session = session if session else ScopedSession()
