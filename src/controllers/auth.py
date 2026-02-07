from typing import Annotated, Final

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from ..dao.session import SessionDepend
from ..dto.auth import (
    RequestForBlacklistAdd,
    RequestForBlacklistDelete,
    RequestForRefreshToken,
    ResponseForBlacklistOperation,
    ResponseForGetCurrentUser,
    ResponseForLogin,
    ResponseForRefreshToken,
)
from ..libs.enum import AuthorityEnum
from ..libs.openapi_tags import TagNameEnum
from ..services.authority import AuthorityService
from ..services.authorize import AuthorizeService, UserDepends
from ..services.token_blacklist import TokenBlacklistService

router: Final[APIRouter] = APIRouter()
tagname: Final[str] = TagNameEnum.AUTH.value


@router.post(
    "/token",
    response_model=ResponseForLogin,
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDepend,
) -> ResponseForLogin:
    """
    ログインしてアクセストークンを取得する
    """
    res = AuthorizeService(session=session).login(form_data)
    return ResponseForLogin(**res.model_dump())


@router.post(
    "/refresh",
    response_model=ResponseForRefreshToken,
)
def refresh_token(
    body: RequestForRefreshToken,
    session: SessionDepend,
) -> ResponseForRefreshToken:
    """
    リフレッシュトークンからアクセストークンを再発行する
    """
    res = AuthorizeService(session=session).refresh(body.refresh_token)
    return ResponseForRefreshToken(**res.model_dump())


@router.post(
    "/auth/blacklist",
    response_model=ResponseForBlacklistOperation,
)
def add_blacklist(
    body: RequestForBlacklistAdd,
    user: UserDepends,
) -> ResponseForBlacklistOperation:
    """
    リフレッシュトークンブラックリストに追加する(管理者のみ)
    """
    AuthorityService(user).check_authority(AuthorityEnum.ADMIN)
    service = TokenBlacklistService()
    if body.mode == "jti":
        service.deny_jti(body.jti, None, body.reason)
    else:
        service.deny_family(body.user, body.family, None, body.reason)
    return ResponseForBlacklistOperation(detail="ok")


@router.delete(
    "/auth/blacklist",
    response_model=ResponseForBlacklistOperation,
)
def delete_blacklist(
    body: RequestForBlacklistDelete,
    user: UserDepends,
) -> ResponseForBlacklistOperation:
    """
    リフレッシュトークンブラックリストから削除する(管理者のみ)
    """
    AuthorityService(user).check_authority(AuthorityEnum.ADMIN)
    service = TokenBlacklistService()
    if body.mode == "jti":
        service.remove_jti(body.jti)
    else:
        service.remove_family(body.user, body.family)
    return ResponseForBlacklistOperation(detail="ok")


@router.get(
    "/me",
    response_model=ResponseForGetCurrentUser,
)
def me(user: UserDepends) -> ResponseForGetCurrentUser:
    """
    ログインユーザ情報を取得する
    """
    return ResponseForGetCurrentUser(name=user.name, authority=user.authority)
