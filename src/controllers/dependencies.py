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
    """
    クエリパラメータからページ情報を生成する。

    Args:
        page: 1始まりのページ番号
        size: 1ページあたりの件数

    Returns:
        ページ情報
    """
    return Page(number=page, size=size)


PageDepend = Annotated[Page, Depends(get_page)]


def usecase_dependency[TUsecase: UsecaseBase](
    usecase_class: type[TUsecase],
    *,
    required_authority: AuthorityEnum,
) -> Callable[..., TUsecase]:
    """
    ユースケースを生成する FastAPI の依存関数を返す。

    Args:
        usecase_class: 生成するユースケースクラス
        required_authority: 実行に必要な権限レベル

    Returns:
        セッションと実行ユーザーを受け取る依存関数
    """

    def dependency(
        session: SessionDepend,
        user: UserDepends,
    ) -> TUsecase:
        """注入されたセッションと実行ユーザーでユースケースを生成する。"""
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
    """
    ページ情報を受け取るユースケース用の依存関数を返す。

    Args:
        usecase_class: 生成するユースケースクラス
        required_authority: 実行に必要な権限レベル

    Returns:
        セッション、実行ユーザー、ページ情報を受け取る依存関数
    """

    def dependency(
        session: SessionDepend,
        user: UserDepends,
        page: PageDepend,
    ) -> TUsecase:
        """注入されたセッション、実行ユーザー、ページ情報でユースケースを生成する。"""
        return usecase_class(
            session=session,
            user=user,
            required_authority=required_authority,
            page=page,
        )

    return dependency
