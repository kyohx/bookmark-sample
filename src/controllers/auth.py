from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from ..dao.session import SessionDepend
from ..dto.auth import ResponseForGetCurrentUser, ResponseForLogin
from ..services.auth import AuthorizeService, UserDepends

router = APIRouter()


@router.post(
    "/token",
    response_model=ResponseForLogin,
    tags=["auth"],
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


@router.get(
    "/me",
    response_model=ResponseForGetCurrentUser,
    tags=["auth"],
)
def me(user: UserDepends) -> ResponseForGetCurrentUser:
    """
    ログインユーザ情報を取得する
    """
    return ResponseForGetCurrentUser(name=user.name, authority=user.authority)
