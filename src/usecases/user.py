from ..dto.user.add import RequestForAddUser
from ..dto.user.update import RequestForUpdateUser
from ..entities.user import UserEntity
from ..libs.enum import AuthorityEnum
from ..repositories.user import UserRepository
from ..services.authorize import AuthorizeService
from .base import UsecaseBase


class UserUsecase(UsecaseBase):
    """
    ユーザーユースケース
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_repository = UserRepository(self.session, page=self.page)

    def add(self, request_body: RequestForAddUser) -> dict:
        """
        新しいユーザーを追加する。

        Args:
            request_body: 追加するユーザーのリクエストデータ

        Returns:
            空の辞書(追加成功を示す)
        """
        user = UserEntity(
            name=request_body.name,
            hashed_password=AuthorizeService.get_hashed_password(
                request_body.password.get_secret_value()
            ),
            disabled=False,
            authority=request_body.authority,
        )
        self.user_repository.add_one(user)

        return {}

    def update(self, request_body: RequestForUpdateUser, name: str) -> dict:
        """
        既存のユーザー情報を更新する。

        Args:
            request_body: 更新するユーザーのリクエストデータ
            name: 更新対象のユーザー名

        Returns:
            レスポンスの辞書

        Raises:
            AuthorityService.Error: ユーザーが更新権限を持っていない
            OperationError: 自分自身の特定のフィールドを変更しようとした
        """
        self.authority_service.check_authority_for_update_user(name)

        user = self.user_repository.find_one(name=name)

        for k, v in request_body.model_dump(exclude_none=True).items():
            if k == "password":
                setattr(
                    user,
                    "hashed_password",
                    AuthorizeService.get_hashed_password(v.get_secret_value()),
                )
            elif self.user.name == name and k in ("name", "disabled", "authority"):
                # 自分自身のname,disabled,authorityは変更できない
                raise self.OperationError(f"You can not change your own {k} value.")
            else:
                setattr(user, k, v)

        self.user_repository.update_one(user)

        return {"updated_user": user.to_response_dict()}

    def get_one(self, name: str) -> dict:
        """
        指定されたユーザーを取得する。

        Args:
            name: 取得対象のユーザー名

        Returns:
            レスポンスの辞書
        """
        user = self.user_repository.find_one(name=name)

        return {"user": user.to_response_dict()}

    def get_list(self) -> dict:
        """
        全てのユーザーのリストを取得する。

        Returns:
            レスポンスの辞書
        """
        user_list = self.user_repository.find_all()

        return {"users": [user.to_response_dict() for user in user_list]}
