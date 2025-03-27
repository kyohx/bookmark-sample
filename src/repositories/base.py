from sqlalchemy.orm.session import Session


class RepositoryError(Exception):
    pass


class BaseRepository:
    """
    レポジトリベースクラス
    外部データ(DB等)に対し操作する
    """

    class Error(RepositoryError):
        pass

    class NotFoundError(RepositoryError):
        pass

    def __init__(self, session: Session) -> None:
        """
        初期化

        :param session: セッション
        """
        self.session = session
