from sqlalchemy.orm.session import Session

from ..libs.config import get_config


class ServiceError(Exception):
    pass


class ServiceBase:
    """
    サービス基底クラス
    """

    class Error(ServiceError):
        pass

    def __init__(self, session: Session) -> None:
        """
        初期化

        :param session: セッション
        """
        self.session = session
        self.config = get_config()
