from ..dto.auth import RequestForBlacklistAddFamily, RequestForBlacklistAddJti
from ..repositories.base import BaseRepository
from ..services.token_blacklist import TokenBlacklistService
from .base import UsecaseBase


class BlacklistUsecase(UsecaseBase):
    """
    リフレッシュトークンブラックリストのユースケース
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.token_blacklist_service = TokenBlacklistService()

    def add_jti(self, request_body: RequestForBlacklistAddJti) -> dict:
        """
        jtiをブラックリストに追加する。
        """
        self.token_blacklist_service.deny_jti(
            request_body.jti,
            None,
            request_body.reason,
        )
        return {}

    def add_family(self, request_body: RequestForBlacklistAddFamily) -> dict:
        """
        user+familyをブラックリストに追加する。
        """
        self.token_blacklist_service.deny_family(
            request_body.user,
            request_body.family,
            None,
            request_body.reason,
        )
        return {}

    def delete_jti(self, jti: str) -> dict:
        """
        jtiのブラックリストを削除する。
        """
        if not self.token_blacklist_service.is_jti_denied(jti):
            raise BaseRepository.NotFoundError("Blacklist jti not found")
        self.token_blacklist_service.remove_jti(jti)
        return {}

    def delete_family(self, user: str, family: str) -> dict:
        """
        user+familyのブラックリストを削除する。
        """
        if not self.token_blacklist_service.is_family_denied(user, family):
            raise BaseRepository.NotFoundError("Blacklist family not found")
        self.token_blacklist_service.remove_family(user, family)
        return {}
