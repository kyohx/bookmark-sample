from sqlalchemy.orm.session import Session

from ..entities.user import UserEntity
from ..libs.enum import AuthorityEnum
from ..libs.page import Page
from ..services.authority import AuthorityService


class UsecaseError(Exception):
    pass


class UsecaseBase:
    """
    ユースケース基底クラス
    """

    class OperationError(UsecaseError):
        """
        操作エラー
        """

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
        self.authority_service = AuthorityService(user)
        "権限サービス"

        self.authority_service.check_authority(required_authority)
