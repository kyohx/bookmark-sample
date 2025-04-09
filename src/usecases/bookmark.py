from ..dto.bookmark.add import RequestForAddBookmark
from ..dto.bookmark.update import RequestForUpdateBookmark
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

    def add(self, request_body: RequestForAddBookmark) -> dict:
        """
        追加
        """
        bookmark = BookmarkEntity(**request_body.model_dump())
        bookmark.hashed_id = get_hashed_id(str(bookmark.url))
        self.bookmark_repository.add_one(bookmark)

        return {"hashed_id": bookmark.hashed_id}

    def update(self, request_body: RequestForUpdateBookmark, hashed_id: str) -> dict:
        """
        更新
        """
        bookmark = self.bookmark_repository.find_one(hashed_id=hashed_id)

        for k, v in request_body.model_dump(exclude_none=True).items():
            setattr(bookmark, k, v)

        self.bookmark_repository.update_one(bookmark)

        return {"updated_bookmark": bookmark.model_dump()}

    def delete(self, hashed_id: str) -> dict:
        """
        削除
        """
        self.bookmark_repository.delete_one(hashed_id=hashed_id)

        return {}

    def get_one(self, hashed_id: str) -> dict:
        """
        取得
        """
        bookmark = self.bookmark_repository.find_one(hashed_id=hashed_id)

        return {"bookmark": bookmark.model_dump()}

    def get_list(self, tag_names: list[str] | None = None) -> dict:
        """
        リスト取得
        """
        if tag_names:
            bookmark_list = self.bookmark_repository.find_by_tags(tag_names)
        else:
            bookmark_list = self.bookmark_repository.find_all()

        return {"bookmarks": [bookmark.model_dump(exclude_none=True) for bookmark in bookmark_list]}
