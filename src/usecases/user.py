from ..dto.user.add import RequestForAddUser
from ..dto.user.update import RequestForUpdateUser
from ..entities.user import UserEntity
from ..libs.authority import check_authority_for_update_user
from ..repositories.user import UserRepository
from ..services.auth import AuthorizeService
from .base import UsecaseBase


class UserUsecase(UsecaseBase):
    """
    ユーザーユースケース
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_repository = UserRepository(self.session)

    def add(self, request_body: RequestForAddUser) -> dict:
        """
        追加
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
        更新
        """
        check_authority_for_update_user(self.user, name)

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
                raise self.Error(f"You can not change your own {k} value.")
            else:
                setattr(user, k, v)

        self.user_repository.update_one(user)

        return {"updated_user": user.to_response_dict()}

    def get_one(self, name: str) -> dict:
        """
        取得
        """
        user = self.user_repository.find_one(name=name)

        return {"user": user.to_response_dict()}

    def get_list(self) -> dict:
        """
        リスト取得
        """
        user_list = self.user_repository.find_all()

        return {"users": [user.to_response_dict() for user in user_list]}
