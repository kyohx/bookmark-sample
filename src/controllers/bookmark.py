from fastapi import APIRouter

from ..dao.session import SessionDepend
from ..dto.bookmark.add import RequestForAddBookmark, ResponseForAddBookmark
from ..dto.bookmark.delete import ResponseForDeleteBookmark
from ..dto.bookmark.get import ResponseForGetBookmark
from ..dto.bookmark.get_list import ResponseForGetBookmarkList
from ..dto.bookmark.update import RequestForUpdateBookmark, ResponseForUpdateBookmark
from ..libs.auth import UserDepends
from ..libs.constraints import PATH_HASHED_ID, QUERY_TAGS
from ..libs.enum import AuthorityEnum
from ..usecases.bookmark import BookmarkUsecase

router = APIRouter()


@router.post(
    "/bookmarks",
    response_model=ResponseForAddBookmark,
)
def add_bookmark(
    req: RequestForAddBookmark,
    session: SessionDepend,
    user: UserDepends,
) -> ResponseForAddBookmark:
    """
    ブックマーク追加
    """
    return BookmarkUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.READWRITE,
    ).add(req)


@router.patch(
    "/bookmarks/{hashed_id}",
    response_model=ResponseForUpdateBookmark,
)
def update_bookmark(
    hashed_id: PATH_HASHED_ID,
    req: RequestForUpdateBookmark,
    session: SessionDepend,
    user: UserDepends,
) -> ResponseForUpdateBookmark:
    """
    ブックマーク更新
    """
    return BookmarkUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.READWRITE,
    ).update(req, hashed_id)


@router.delete(
    "/bookmarks/{hashed_id}",
    response_model=ResponseForDeleteBookmark,
)
def delete_bookmark(
    hashed_id: PATH_HASHED_ID,
    session: SessionDepend,
    user: UserDepends,
) -> ResponseForDeleteBookmark:
    """
    ブックマーク削除
    """
    return BookmarkUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.READWRITE,
    ).delete(hashed_id)


@router.get(
    "/bookmarks/{hashed_id}",
    response_model=ResponseForGetBookmark,
)
def get_bookmark(
    hashed_id: PATH_HASHED_ID,
    session: SessionDepend,
    user: UserDepends,
) -> ResponseForGetBookmark:
    """
    ブックマーク取得
    """
    return BookmarkUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.READ,
    ).get_one(hashed_id)


@router.get(
    "/bookmarks",
    response_model=ResponseForGetBookmarkList,
)
def get_bookmarks(
    session: SessionDepend,
    user: UserDepends,
    tag: QUERY_TAGS = None,
) -> ResponseForGetBookmarkList:
    """
    ブックマークリスト取得
    """
    return BookmarkUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.READ,
    ).get_list(tag_names=tag)
