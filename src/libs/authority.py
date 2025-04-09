from fastapi import HTTPException, status

from ..entities.user import UserEntity
from .enum import AuthorityEnum


def check_authority(user: UserEntity, required_authority: AuthorityEnum) -> None:
    """
    権限チェック
    """
    if user.authority.value < required_authority.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access",
        )


def check_authority_for_update_user(user: UserEntity, target_user_name: str) -> None:
    """
    ユーザー更新の権限チェック
    """
    if user.authority is AuthorityEnum.ADMIN:
        return

    if user.name != target_user_name:
        # 管理者以外は自分以外のユーザーを更新できない
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access",
        )
