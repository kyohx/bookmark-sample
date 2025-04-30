from sqlalchemy.orm.session import Session

from ..entities.user import UserEntity
from ..libs.enum import AuthorityEnum
from ..libs.page import Page


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
        self,
        session: Session,
        user: UserEntity,
        required_authority: AuthorityEnum,
        page: Page | None = None,
    ) -> None:
        """
        ユースケースクラスの初期化処理

        Args:
            session: データベースセッション
            user: ユースケースの実行ユーザーエンティティ
            required_authority: 必要な権限レベル
            page: ページ情報

        Raises:
            AuthorityError: ユーザーが必要な権限を持っていない
        """
        self.session = session
        "セッション"
        self.user = user
        "ユーザー情報"
        self.page = page
        "ページ情報"

        # 権限チェック
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
