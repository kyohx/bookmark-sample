from ..dao.models.bookmark import BookmarkDao
from ..dao.operators.bookmark import BookmarkDaoOperator
from ..dao.operators.bookmark_tag import BookmarkTagDaoOperator
from ..dao.operators.tag import TagDaoOperator
from ..entities.bookmark import BookmarkEntity
from .base import BaseRepository
from .error_handler import error_handler


class BookmarkRepository(BaseRepository):
    """
    ブックマークリポジトリクラス
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bookmark_operator = BookmarkDaoOperator(self.session)
        self.tag_operator = TagDaoOperator(self.session)
        self.bookmark_tag_operator = BookmarkTagDaoOperator(self.session)
        self.loaded_bookmark_dao = None  # 読み込み済みのブックマークDAO(updateで使用)

    @error_handler
    def find_one(self, /, hashed_id: str) -> BookmarkEntity:
        """
        ブックマーク1つを取得する
        """
        bookmark_dao = self.bookmark_operator.find_one_by_hashed_id(hashed_id)
        if not bookmark_dao:
            raise self.NotFoundError("Not found specified data.")

        self.loaded_bookmark_dao = bookmark_dao

        # ループしない前提なのでn+1にはならない
        tags = self.tag_operator.find_by_bookmark_id(bookmark_dao.id)

        params = bookmark_dao.to_dict()
        params["tags"] = [tag.name for tag in tags]

        return BookmarkEntity(**params)

    @error_handler
    def find_all(self) -> list[BookmarkEntity]:
        """
        全ブックマークのリストを取得する
        """
        return [
            BookmarkEntity(**bookmark_dao.to_dict())
            for bookmark_dao in self.bookmark_operator.find_all()
        ]

    @error_handler
    def find_by_tags(self, tag_names: list[str]) -> list[BookmarkEntity]:
        """
        タグ名でブックマークのリストを取得する
        """
        return [
            BookmarkEntity(**bookmark_dao.to_dict())
            for bookmark_dao in self.bookmark_operator.find_by_tags(tag_names)
        ]

    @error_handler
    def save(self, bookmark: BookmarkEntity) -> str:
        """
        ブックマーク情報を保存

        :return: ブックマークのハッシュID
        """
        # ブックマークの保存
        if self.loaded_bookmark_dao:
            bookmark_dao = self.loaded_bookmark_dao
            for k, v in bookmark.model_dump(mode="python", exclude_none=True).items():
                setattr(bookmark_dao, k, v)
        else:
            bookmark_dao = BookmarkDao(**bookmark.model_dump(mode="python", exclude={"tags"}))
        self.bookmark_operator.save(bookmark_dao)

        if bookmark.tags is not None:
            # タグの保存
            tag_dao_list = self.tag_operator.save_by_names(bookmark.tags)
            # ブックマークとタグの紐付け
            self.bookmark_tag_operator.save_by_tags(bookmark_dao.id, tag_dao_list)

        return bookmark_dao.hashed_id

    @error_handler
    def delete(self, /, hashed_id: str):
        """
        ブックマーク情報を削除
        """
        bookmark_dao = self.bookmark_operator.find_one_by_hashed_id(hashed_id)
        if bookmark_dao is None:
            raise self.NotFoundError("Not found specified data.")

        self.bookmark_operator.delete(bookmark_dao)
