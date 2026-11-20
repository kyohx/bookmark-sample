from ..entities.session import RefreshSession
from ..repositories.user import UserRepository
from ..services.token_blacklist import TokenBlacklistService
from .base import UsecaseBase


class SessionUsecase(UsecaseBase):
    """管理者によるユーザーのセッション確認と失効。"""

    def __init__(self, *args, **kwargs) -> None:
        """
        基底クラスで権限を確認し、ユーザーリポジトリとトークンブラックリストサービスを初期化する。

        Args:
            *args: 基底ユースケースに渡す位置引数
            **kwargs: 基底ユースケースに渡すキーワード引数
        """
        super().__init__(*args, **kwargs)
        self.user_repository = UserRepository(self.session)
        self.blacklist_service = TokenBlacklistService()

    def get_list(self, name: str) -> list[RefreshSession]:
        """
        対象ユーザーの存在を確認し、有効期限内のセッションを取得する。

        Args:
            name: 対象ユーザー名

        Returns:
            失効済みも含む有効期限内のセッション一覧

        Raises:
            UserRepository.NotFoundError: 対象ユーザーが存在しない場合
            TokenBlacklistService.Error: Redis を利用できない場合
        """
        self.user_repository.find_one(name)
        return self.blacklist_service.list_sessions(name)

    def revoke(self, name: str, family: str) -> None:
        """
        対象ユーザーの指定セッションを失効させる。

        Args:
            name: 対象ユーザー名
            family: 失効対象のセッションID

        Raises:
            UserRepository.NotFoundError: 対象ユーザーが存在しない場合
            UsecaseBase.NotFoundError: 対象セッションが存在しない場合
            TokenBlacklistService.Error: Redis を利用できない場合、またはセッションの有効期限を取得できない場合
        """
        self.user_repository.find_one(name)
        if not self.blacklist_service.revoke_session(name, family):
            raise self.NotFoundError("Session not found")
