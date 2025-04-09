from sqlalchemy.orm.session import Session

from ..entities.user import UserEntity
from ..libs.authority import check_authority
from ..libs.enum import AuthorityEnum


class UsecaseError(Exception):
    pass


class UsecaseBase:
    """
    ユースケース基底クラス
    """

    class Error(UsecaseError):
        pass

    def __init__(
        self, session: Session, user: UserEntity, required_authority: AuthorityEnum
    ) -> None:
        """
        初期化

        :param session: セッション
        """
        self.session = session
        self.user = user
        check_authority(user, required_authority)
