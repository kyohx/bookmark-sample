from ..dto.bookmark.add import RequestForAddBookmark, ResponseForAddBookmark
from ..dto.bookmark.delete import ResponseForDeleteBookmark
from ..dto.bookmark.get import ResponseForGetBookmark
from ..dto.bookmark.get_list import ResponseForGetBookmarkList
from ..dto.bookmark.update import RequestForUpdateBookmark, ResponseForUpdateBookmark
from ..entities.bookmark import BookmarkEntity
from ..libs.util import get_hashed_id
from ..repositories.bookmark import BookmarkRepository
from .base import UsecaseBase


class BookmarkUsecase(UsecaseBase):
    """
    ブックマークユースケース
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bookmark_repository = BookmarkRepository(self.session)

    def add(self, request_body: RequestForAddBookmark) -> ResponseForAddBookmark:
        """
        追加
        """
        bookmark = BookmarkEntity(**request_body.model_dump())
        bookmark.hashed_id = get_hashed_id(str(bookmark.url))
        self.bookmark_repository.add_one(bookmark)

        res = {
            "hashed_id": bookmark.hashed_id,
        }

        return ResponseForAddBookmark(**res)

    def update(
        self, request_body: RequestForUpdateBookmark, hashed_id: str
    ) -> ResponseForUpdateBookmark:
        """
        更新
        """
        bookmark = self.bookmark_repository.find_one(hashed_id=hashed_id)

        for k, v in request_body.model_dump(exclude_none=True).items():
            setattr(bookmark, k, v)

        self.bookmark_repository.update_one(bookmark)

        res = {"updated_bookmark": bookmark.model_dump()}

        return ResponseForUpdateBookmark(**res)

    def delete(self, hashed_id: str) -> ResponseForDeleteBookmark:
        """
        削除
        """
        self.bookmark_repository.delete_one(hashed_id=hashed_id)

        return ResponseForDeleteBookmark()

    def get_one(self, hashed_id: str) -> ResponseForGetBookmark:
        """
        取得
        """
        bookmark = self.bookmark_repository.find_one(hashed_id=hashed_id)

        res = {"bookmark": bookmark.model_dump()}

        return ResponseForGetBookmark(**res)

    def get_list(self, tag_names: list[str] | None = None) -> ResponseForGetBookmarkList:
        """
        リスト取得
        """
        if tag_names:
            bookmark_list = self.bookmark_repository.find_by_tags(tag_names)
        else:
            bookmark_list = self.bookmark_repository.find_all()

        res = {"bookmarks": [bookmark.model_dump(exclude_none=True) for bookmark in bookmark_list]}

        return ResponseForGetBookmarkList(**res)
