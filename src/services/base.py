from sqlalchemy.orm.session import Session

from ..libs.config import get_config


class ServiceError(Exception):
    pass


class ServiceBase:
    """
    サービス基底クラス
    """

    class Error(ServiceError):
        """
        サービスエラー
        """

        pass

    def __init__(self, session: Session) -> None:
        """
        サービスクラスの初期化

        Args:
            session: データベースセッション
        """
        self.session = session
        "セッション"
        self.config = get_config()
        "設定値"
