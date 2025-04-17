from fastapi import APIRouter

from ..dao.session import SessionDepend
from ..dto.bookmark.add import RequestForAddBookmark, ResponseForAddBookmark
from ..dto.bookmark.delete import ResponseForDeleteBookmark
from ..dto.bookmark.get import ResponseForGetBookmark
from ..dto.bookmark.get_list import ResponseForGetBookmarkList
from ..dto.bookmark.update import RequestForUpdateBookmark, ResponseForUpdateBookmark
from ..libs.constraints import PATH_HASHED_ID, QUERY_TAGS
from ..libs.enum import AuthorityEnum
from ..libs.openapi_tags import TagNameEnum
from ..services.auth import UserDepends
from ..usecases.bookmark import BookmarkUsecase

router = APIRouter()
tagname = TagNameEnum.BOOKMARK.value


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
    res = BookmarkUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.READWRITE,
    ).add(req)

    return ResponseForAddBookmark(**res)


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
    res = BookmarkUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.READWRITE,
    ).update(req, hashed_id)

    return ResponseForUpdateBookmark(**res)


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
    res = BookmarkUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.READWRITE,
    ).delete(hashed_id)

    return ResponseForDeleteBookmark(**res)


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
    res = BookmarkUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.READ,
    ).get_one(hashed_id)

    return ResponseForGetBookmark(**res)


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
    res = BookmarkUsecase(
        session=session,
        user=user,
        required_authority=AuthorityEnum.READ,
    ).get_list(tag_names=tag)

    return ResponseForGetBookmarkList(**res)
