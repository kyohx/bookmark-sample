from sqlalchemy.orm.session import Session


class UsecaseError(Exception):
    pass


class UsecaseBase:
    """
    ユースケース基底クラス
    """

    class Error(UsecaseError):
        pass

    def __init__(self, session: Session) -> None:
        """
        初期化

        :param session: セッション
        """
        self.session = session
