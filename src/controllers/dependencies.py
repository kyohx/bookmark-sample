from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from ..dao.session import SessionDepend
from ..libs.constraints import FIELD_PAGE_NUMBER, FIELD_PAGE_SIZE
from ..libs.enum import AuthorityEnum
from ..libs.page import Page
from ..services.authorize import UserDepends
from ..usecases.base import UsecaseBase


def get_page(
    page: FIELD_PAGE_NUMBER = 1,
    size: FIELD_PAGE_SIZE = 10,
) -> Page:
    return Page(number=page, size=size)


PageDepend = Annotated[Page, Depends(get_page)]


def usecase_dependency[TUsecase: UsecaseBase](
    usecase_class: type[TUsecase],
    *,
    required_authority: AuthorityEnum,
) -> Callable[..., TUsecase]:
    def dependency(
        session: SessionDepend,
        user: UserDepends,
    ) -> TUsecase:
        return usecase_class(
            session=session,
            user=user,
            required_authority=required_authority,
        )

    return dependency


def paged_usecase_dependency[TUsecase: UsecaseBase](
    usecase_class: type[TUsecase],
    *,
    required_authority: AuthorityEnum,
) -> Callable[..., TUsecase]:
    def dependency(
        session: SessionDepend,
        user: UserDepends,
        page: PageDepend,
    ) -> TUsecase:
        return usecase_class(
            session=session,
            user=user,
            required_authority=required_authority,
            page=page,
        )

    return dependency
