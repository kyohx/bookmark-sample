from fastapi import HTTPException

from ..entities.user import User
from .enum import AuthorityEnum


def check_authority(user: User, required_authority: AuthorityEnum) -> None:
    """
    権限チェック
    """
    if user.authority.value < required_authority.value:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access",
        )
