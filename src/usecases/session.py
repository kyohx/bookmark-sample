from ..entities.session import RefreshSession
from ..repositories.user import UserRepository
from ..services.token_blacklist import TokenBlacklistService
from .base import UsecaseBase


class SessionUsecase(UsecaseBase):
    """管理者によるユーザーのセッション確認と失効。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_repository = UserRepository(self.session)
        self.blacklist_service = TokenBlacklistService()

    def get_list(self, name: str) -> list[RefreshSession]:
        self.user_repository.find_one(name)
        return self.blacklist_service.list_sessions(name)

    def revoke(self, name: str, family: str) -> None:
        self.user_repository.find_one(name)
        if not self.blacklist_service.revoke_session(name, family):
            raise self.NotFoundError("Session not found")
