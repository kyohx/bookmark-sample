from typing import Annotated, Final

from fastapi import APIRouter, Depends

from ..dto.bookmark.add import RequestForAddBookmark, ResponseForAddBookmark
from ..dto.bookmark.delete import ResponseForDeleteBookmark
from ..dto.bookmark.get import ResponseForGetBookmark
from ..dto.bookmark.get_list import ResponseForGetBookmarkList
from ..dto.bookmark.update import RequestForUpdateBookmark, ResponseForUpdateBookmark
from ..libs.constraints import PATH_HASHED_ID, QUERY_TAGS
from ..libs.enum import AuthorityEnum
from ..libs.openapi_tags import TagNameEnum
from ..usecases.bookmark import BookmarkUsecase
from .dependencies import paged_usecase_dependency, usecase_dependency

router: Final[APIRouter] = APIRouter()
tagname: Final[str] = TagNameEnum.BOOKMARK.value

ReadWriteBookmarkUsecaseDepend = Annotated[
    BookmarkUsecase,
    Depends(usecase_dependency(BookmarkUsecase, required_authority=AuthorityEnum.READWRITE)),
]
ReadBookmarkUsecaseDepend = Annotated[
    BookmarkUsecase,
    Depends(usecase_dependency(BookmarkUsecase, required_authority=AuthorityEnum.READ)),
]
PagedReadBookmarkUsecaseDepend = Annotated[
    BookmarkUsecase,
    Depends(paged_usecase_dependency(BookmarkUsecase, required_authority=AuthorityEnum.READ)),
]


@router.post(
    "/bookmarks",
    response_model=ResponseForAddBookmark,
)
def add_bookmark(
    req: RequestForAddBookmark,
    usecase: ReadWriteBookmarkUsecaseDepend,
) -> ResponseForAddBookmark:
    """
    ブックマーク追加
    """
    res = usecase.add(req)

    return ResponseForAddBookmark(**res)


@router.patch(
    "/bookmarks/{hashed_id}",
    response_model=ResponseForUpdateBookmark,
)
def update_bookmark(
    hashed_id: PATH_HASHED_ID,
    req: RequestForUpdateBookmark,
    usecase: ReadWriteBookmarkUsecaseDepend,
) -> ResponseForUpdateBookmark:
    """
    ブックマーク更新
    """
    res = usecase.update(req, hashed_id)

    return ResponseForUpdateBookmark(**res)


@router.delete(
    "/bookmarks/{hashed_id}",
    response_model=ResponseForDeleteBookmark,
)
def delete_bookmark(
    hashed_id: PATH_HASHED_ID,
    usecase: ReadWriteBookmarkUsecaseDepend,
) -> ResponseForDeleteBookmark:
    """
    ブックマーク削除
    """
    res = usecase.delete(hashed_id)

    return ResponseForDeleteBookmark(**res)


@router.get(
    "/bookmarks/{hashed_id}",
    response_model=ResponseForGetBookmark,
)
def get_bookmark(
    hashed_id: PATH_HASHED_ID,
    usecase: ReadBookmarkUsecaseDepend,
) -> ResponseForGetBookmark:
    """
    ブックマーク取得
    """
    res = usecase.get_one(hashed_id)

    return ResponseForGetBookmark(**res)


@router.get(
    "/bookmarks",
    response_model=ResponseForGetBookmarkList,
)
def get_bookmarks(
    usecase: PagedReadBookmarkUsecaseDepend,
    tag: QUERY_TAGS = None,
) -> ResponseForGetBookmarkList:
    """
    ブックマークリスト取得
    """
    res = usecase.get_list(tag_names=tag)

    return ResponseForGetBookmarkList(**res)
