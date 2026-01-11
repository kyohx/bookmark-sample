from typing import Final

from fastapi import APIRouter

from ..dao.session import SessionDepend
from ..dto.user.add import RequestForAddUser, ResponseForAddUser
from ..dto.user.get import ResponseForGetUser
from ..dto.user.get_list import ResponseForGetUserList
from ..dto.user.update import RequestForUpdateUser, ResponseForUpdateUser
from ..libs.constraints import FIELD_PAGE_NUMBER, FIELD_PAGE_SIZE, FIELD_STRING_USERNAME
from ..libs.enum import AuthorityEnum
from ..libs.openapi_tags import TagNameEnum
from ..libs.page import Page
from ..services.authorize import UserDepends
from ..usecases.user import UserUsecase

router: Final[APIRouter] = APIRouter()
tagname: Final[str] = TagNameEnum.USER.value


@router.post(
    "/users",
    response_model=ResponseForAddUser,
)
def add_user(
    req: RequestForAddUser,
    session: SessionDepend,
    user: UserDepends,
) -> ResponseForAddUser:
    """
    ユーザー追加
    """
    res = UserUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.ADMIN,
    ).add(req)

    return ResponseForAddUser(**res)


@router.patch(
    "/users/{name}",
    response_model=ResponseForUpdateUser,
)
def update_user(
    name: FIELD_STRING_USERNAME,
    req: RequestForUpdateUser,
    session: SessionDepend,
    user: UserDepends,
) -> ResponseForUpdateUser:
    """
    ユーザー更新
     - ログインユーザー自身のname,disabled,authorityは変更できない
     - 管理者以外はログインユーザー自身の情報のみ変更可能
    """
    res = UserUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.NONE,
    ).update(req, name)

    return ResponseForUpdateUser(**res)


@router.get(
    "/users/{name}",
    response_model=ResponseForGetUser,
)
def get_user(
    name: FIELD_STRING_USERNAME,
    session: SessionDepend,
    user: UserDepends,
) -> ResponseForGetUser:
    """
    ユーザー取得
    """
    res = UserUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.ADMIN,
    ).get_one(name)

    return ResponseForGetUser(**res)


@router.get(
    "/users",
    response_model=ResponseForGetUserList,
)
def get_users(
    session: SessionDepend,
    user: UserDepends,
    page: FIELD_PAGE_NUMBER = 1,
    size: FIELD_PAGE_SIZE = 10,
) -> ResponseForGetUserList:
    """
    ユーザーリスト取得
    """
    res = UserUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.ADMIN,
        page=Page(number=page, size=size),
    ).get_list()

    return ResponseForGetUserList(**res)
