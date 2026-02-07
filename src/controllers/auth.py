from typing import Annotated, Final

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from ..dao.session import SessionDepend
from ..dto.auth import (
    RequestForBlacklistAddFamily,
    RequestForBlacklistAddJti,
    RequestForRefreshToken,
    ResponseForGetCurrentUser,
    ResponseForLogin,
    ResponseForRefreshToken,
)
from ..libs.constraints import FIELD_STRING_FAMILY, FIELD_STRING_JTI, FIELD_STRING_USERNAME
from ..libs.enum import AuthorityEnum
from ..libs.openapi_tags import TagNameEnum
from ..services.authorize import AuthorizeService, UserDepends
from ..usecases.blacklist import BlacklistUsecase

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
    req: RequestForRefreshToken,
    session: SessionDepend,
) -> ResponseForRefreshToken:
    """
    リフレッシュトークンからアクセストークンを再発行する
    """
    res = AuthorizeService(session=session).refresh(req.refresh_token)
    return ResponseForRefreshToken(**res.model_dump())


@router.post(
    "/auth/blacklist/jti",
    status_code=status.HTTP_204_NO_CONTENT,
)
def add_blacklist_jti(
    req: RequestForBlacklistAddJti,
    session: SessionDepend,
    user: UserDepends,
) -> Response:
    """
    jtiをリフレッシュトークンブラックリストに追加する(管理者のみ)
    """
    BlacklistUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.ADMIN,
    ).add_jti(req)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/auth/blacklist/family",
    status_code=status.HTTP_204_NO_CONTENT,
)
def add_blacklist_family(
    req: RequestForBlacklistAddFamily,
    session: SessionDepend,
    user: UserDepends,
) -> Response:
    """
    user+familyをリフレッシュトークンブラックリストに追加する(管理者のみ)
    """
    BlacklistUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.ADMIN,
    ).add_family(req)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/auth/blacklist/jti/{jti}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_blacklist_jti(
    jti: FIELD_STRING_JTI,
    session: SessionDepend,
    user: UserDepends,
) -> Response:
    """
    jtiのリフレッシュトークンブラックリストを削除する(管理者のみ)
    """
    BlacklistUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.ADMIN,
    ).delete_jti(jti)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/auth/blacklist/family/{user}/{family}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_blacklist_family(
    user: FIELD_STRING_USERNAME,
    family: FIELD_STRING_FAMILY,
    session: SessionDepend,
    current_user: UserDepends,
) -> Response:
    """
    user+familyのリフレッシュトークンブラックリストを削除する(管理者のみ)
    """
    BlacklistUsecase(
        session=session,
        user=current_user,
        required_authority=AuthorityEnum.ADMIN,
    ).delete_family(user, family)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=ResponseForGetCurrentUser,
)
def me(user: UserDepends) -> ResponseForGetCurrentUser:
    """
    ログインユーザ情報を取得する
    """
    return ResponseForGetCurrentUser(name=user.name, authority=user.authority)
