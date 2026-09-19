from typing import Annotated, Final

from fastapi import APIRouter, Depends

from ..dto.user.add import RequestForAddUser, ResponseForAddUser
from ..dto.user.get import ResponseForGetUser
from ..dto.user.get_list import ResponseForGetUserList
from ..dto.user.update import RequestForUpdateUser, ResponseForUpdateUser
from ..libs.constraints import FIELD_STRING_USERNAME
from ..libs.enum import AuthorityEnum
from ..libs.openapi_tags import TagNameEnum
from ..usecases.user import UserUsecase
from .dependencies import paged_usecase_dependency, usecase_dependency

router: Final[APIRouter] = APIRouter()
tagname: Final[str] = TagNameEnum.USER.value

AdminUserUsecaseDepend = Annotated[
    UserUsecase,
    Depends(usecase_dependency(UserUsecase, required_authority=AuthorityEnum.ADMIN)),
]
UserUpdateUsecaseDepend = Annotated[
    UserUsecase,
    Depends(usecase_dependency(UserUsecase, required_authority=AuthorityEnum.NONE)),
]
PagedAdminUserUsecaseDepend = Annotated[
    UserUsecase,
    Depends(paged_usecase_dependency(UserUsecase, required_authority=AuthorityEnum.ADMIN)),
]


@router.post(
    "/users",
    response_model=ResponseForAddUser,
)
def add_user(
    req: RequestForAddUser,
    usecase: AdminUserUsecaseDepend,
) -> ResponseForAddUser:
    """
    ユーザー追加
    """
    user = usecase.add(req)
    return ResponseForAddUser.from_entity(user)


@router.patch(
    "/users/{name}",
    response_model=ResponseForUpdateUser,
)
def update_user(
    name: FIELD_STRING_USERNAME,
    req: RequestForUpdateUser,
    usecase: UserUpdateUsecaseDepend,
) -> ResponseForUpdateUser:
    """
    ユーザー更新
     - ログインユーザー自身のname,disabled,authorityは変更できない
     - 管理者以外はログインユーザー自身の情報のみ変更可能
    """
    user = usecase.update(req, name)
    return ResponseForUpdateUser.from_entity(user)


@router.get(
    "/users/{name}",
    response_model=ResponseForGetUser,
)
def get_user(
    name: FIELD_STRING_USERNAME,
    usecase: AdminUserUsecaseDepend,
) -> ResponseForGetUser:
    """
    ユーザー取得
    """
    user = usecase.get_one(name)
    return ResponseForGetUser.from_entity(user)


@router.get(
    "/users",
    response_model=ResponseForGetUserList,
)
def get_users(
    usecase: PagedAdminUserUsecaseDepend,
) -> ResponseForGetUserList:
    """
    ユーザーリスト取得
    """
    users = usecase.get_list()
    return ResponseForGetUserList.from_entities(users)
