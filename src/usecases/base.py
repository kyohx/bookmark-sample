from sqlalchemy.orm.session import Session

from ..entities.user import UserEntity
from ..libs.enum import AuthorityEnum


class UsecaseError(Exception):
    pass


class UsecaseBase:
    """
    ユースケース基底クラス
    """

    class Error(UsecaseError):
        pass

    class AuthorityError(UsecaseError):
        pass

    class OperationError(UsecaseError):
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
        self._check_authority(required_authority)

    def _check_authority(self, required_authority: AuthorityEnum) -> None:
        """
        権限チェック
        """
        if self.user.authority.value < required_authority.value:
            raise self.AuthorityError("You don't have permission to access")
