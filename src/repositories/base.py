from sqlalchemy.orm.session import Session

from ..libs.page import Page


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

    def __init__(
        self,
        session: Session,
        page: Page | None = None,
    ) -> None:
        """
        初期化処理

        Args:
            session: データベースセッション
            page: ページ情報
        """
        self.session = session
        "セッション"
        self.page = page
        "ページ情報"
