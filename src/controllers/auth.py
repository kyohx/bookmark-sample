from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from ..dao.session import SessionDepend
from ..dto.auth import ResponseForGetCurrentUser, ResponseForLogin
from ..libs.auth import UserDepends, login_for_access_token

router = APIRouter()


@router.post("/token")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDepend,
) -> ResponseForLogin:
    """
    ログインしてアクセストークンを取得する
    """
    res = login_for_access_token(form_data, session)
    return ResponseForLogin(**res.model_dump())


@router.get("/me")
def me(user: UserDepends) -> ResponseForGetCurrentUser:
    """
    現在のユーザ情報を取得する
    """
    return ResponseForGetCurrentUser(name=user.name)
