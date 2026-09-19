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
        self.bookmark_repository = BookmarkRepository(self.session, page=self.page)

    def add(self, request_body: RequestForAddBookmark) -> BookmarkEntity:
        """
        新しいブックマークを追加する。

        Args:
            request_body: 追加するブックマークのリクエストデータ

        Returns:
            追加後のブックマーク
        """
        bookmark = BookmarkEntity(**request_body.model_dump())
        bookmark.hashed_id = get_hashed_id(str(bookmark.url))
        self.bookmark_repository.add_one(bookmark)

        return bookmark

    def update(self, request_body: RequestForUpdateBookmark, hashed_id: str) -> BookmarkEntity:
        """
        既存のブックマークを更新する。

        Args:
            request_body: 更新するブックマークのリクエストデータ
            hashed_id: 更新対象のブックマークのハッシュID

        Returns:
            更新後のブックマーク
        """
        bookmark = self.bookmark_repository.find_one(hashed_id=hashed_id)

        for k, v in request_body.model_dump(exclude_none=True).items():
            setattr(bookmark, k, v)

        self.bookmark_repository.update_one(bookmark, current_hashed_id=hashed_id)

        return bookmark

    def delete(self, hashed_id: str) -> None:
        """
        指定されたハッシュIDのブックマークを削除する。

        Args:
            hashed_id: 削除対象のブックマークのハッシュID

        Returns:
            なし
        """
        self.bookmark_repository.delete_one(hashed_id=hashed_id)

    def get_one(self, hashed_id: str) -> BookmarkEntity:
        """
        指定されたハッシュIDのブックマークを取得する。

        Args:
            hashed_id: 取得対象のブックマークのハッシュID

        Returns:
            取得したブックマーク
        """
        bookmark = self.bookmark_repository.find_one(hashed_id=hashed_id)

        return bookmark

    def get_list(self, tag_names: list[str] | None = None) -> list[BookmarkEntity]:
        """
        ブックマークのリストを取得する。

        Args:
            tag_names: フィルタリング対象のタグ名のリスト

        Returns:
            ブックマークリスト
        """
        if tag_names:
            bookmark_list = self.bookmark_repository.find_by_tags(tag_names)
        else:
            bookmark_list = self.bookmark_repository.find_all()

        return bookmark_list
