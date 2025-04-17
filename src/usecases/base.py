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
        ユースケースクラスの初期化処理

        Args:
            session: データベースセッション
            user: ユースケースの実行ユーザーエンティティ
            required_authority: 必要な権限レベル

        Raises:
            AuthorityError: ユーザーが必要な権限を持っていない
        """
        self.session = session
        self.user = user
        self._check_authority(required_authority)

    def _check_authority(self, required_authority: AuthorityEnum) -> None:
        """
        ユーザーの権限をチェックする。

        Args:
            required_authority: 必要な権限レベル

        Raises:
            AuthorityError: ユーザーが必要な権限を持っていない
        """
        if self.user.authority.value < required_authority.value:
            raise self.AuthorityError("You don't have permission to access")
