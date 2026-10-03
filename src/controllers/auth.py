from typing import Annotated, Final

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from ..dao.session import SessionDepend
from ..dto.auth import (
    RequestForRefreshToken,
    ResponseForGetCurrentUser,
    ResponseForLogin,
    ResponseForRefreshToken,
)
from ..libs.openapi_tags import TagNameEnum
from ..services.authorize import AuthorizeService, UserDepends

router: Final[APIRouter] = APIRouter()
tagname: Final[str] = TagNameEnum.AUTH.value


@router.post(
    "/token",
    response_model=ResponseForLogin,
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDepend,
    request: Request,
) -> ResponseForLogin:
    """
    ログインしてアクセストークンを取得する
    """
    res = AuthorizeService(session=session).login(form_data, request.headers.get("user-agent"))
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


@router.get(
    "/me",
    response_model=ResponseForGetCurrentUser,
)
def me(user: UserDepends) -> ResponseForGetCurrentUser:
    """
    ログインユーザ情報を取得する
    """
    return ResponseForGetCurrentUser(name=user.name, authority=user.authority)
