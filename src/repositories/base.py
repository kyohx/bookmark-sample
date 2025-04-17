from sqlalchemy.orm.session import Session


class RepositoryError(Exception):
    pass


class BaseRepository:
    """
    レポジトリベースクラス
    外部データ(DB等)に対し操作する
    """

    class Error(RepositoryError):
        """
        レポジトリエラー
        """

        pass

    class NotFoundError(RepositoryError):
        """
        データが見つからない
        """

        pass

    def __init__(self, session: Session) -> None:
        """
        初期化処理

        Args:
            session: データベースセッション
        """
        self.session = session
