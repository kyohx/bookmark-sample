from .base import ServiceBase, ServiceError
from ..libs.enum import AuthorityEnum
from ..entities.user import UserEntity


class AuthorityService(ServiceBase):
    """
    ユーザー権限サービス
    """

    class Error(ServiceError):
        """
        権限サービスエラー
        """

        pass

    def __init__(self, user: UserEntity) -> None:
        """
        初期化処理

        Args:
            user: ユーザーエンティティ

        """
        self.user = user
        "ユーザー情報"

    def check_authority(self, required_authority: AuthorityEnum) -> None:
        """
        ユーザーの権限をチェックする。

        Args:
            required_authority: 必要な権限レベル

        Raises:
            Error: ユーザーが必要な権限を持っていない
        """
        if self.user.authority.value < required_authority.value:
            raise self.Error("You don't have permission to access")

    def check_authority_for_update_user(self, target_user_name: str) -> None:
        """
        ユーザー情報更新処理の場合の権限チェックを行う。

        Args:
            target_user_name: 更新対象のユーザー名

        Raises:
            Error: ユーザーが更新権限を持っていない
        """
        if self.user.authority is AuthorityEnum.ADMIN:
            return

        if self.user.name != target_user_name:
            # 管理者以外は自分以外のユーザーを更新できない
            raise self.Error("You don't have permission to access")
