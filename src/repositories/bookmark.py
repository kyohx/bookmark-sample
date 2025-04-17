from ..dao.models.bookmark import BookmarkDao
from ..dao.operators.bookmark import BookmarkDaoOperator
from ..dao.operators.bookmark_tag import BookmarkTagDaoOperator
from ..dao.operators.tag import TagDaoOperator
from ..entities.bookmark import BookmarkEntity
from .base import BaseRepository


class BookmarkRepository(BaseRepository):
    """
    ブックマークリポジトリクラス
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bookmark_operator = BookmarkDaoOperator(self.session)
        self.tag_operator = TagDaoOperator(self.session)
        self.bookmark_tag_operator = BookmarkTagDaoOperator(self.session)
        self.loaded_bookmark_dao: BookmarkDao | None = None

    def find_one(self, /, hashed_id: str) -> BookmarkEntity:
        """
        指定されたハッシュIDに対応するブックマークを1件取得する。

        Args:
            hashed_id: ブックマークのハッシュID

        Returns:
            取得したブックマークエンティティ

        Raises:
            NotFoundError: 指定されたハッシュIDに対応するデータが見つからない
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

    def find_all(self) -> list[BookmarkEntity]:
        """
        全てのブックマークを取得する。

        Returns:
            ブックマークエンティティのリスト
        """
        return [
            BookmarkEntity(**bookmark_dao.to_dict())
            for bookmark_dao in self.bookmark_operator.find_all()
        ]

    def find_by_tags(self, tag_names: list[str]) -> list[BookmarkEntity]:
        """
        指定されたタグ名に関連付けられたブックマークを取得する。

        Args:
            tag_names: 検索対象のタグ名のリスト

        Returns:
            list[BookmarkEntity]: 指定されたタグに関連付けられたブックマークエンティティのリスト
        """
        return [
            BookmarkEntity(**bookmark_dao.to_dict())
            for bookmark_dao in self.bookmark_operator.find_by_tags(tag_names)
        ]

    def add_one(self, bookmark: BookmarkEntity) -> None:
        """
        新しいブックマークを追加する。

        Args:
            bookmark: 追加するブックマークエンティティ
        """
        bookmark_dao = BookmarkDao(**bookmark.model_dump(exclude={"tags"}))

        self.bookmark_operator.save(bookmark_dao)
        self._save_tags(bookmark.tags, bookmark_dao.id)

    def update_one(self, bookmark: BookmarkEntity) -> None:
        """
        既存のブックマークを更新する。

        事前に `find_one()` を使用して更新対象のブックマークを取得しておく必要がある。

        Args:
            bookmark: 更新するブックマークエンティティ

        Raises:
            Error: 更新対象のブックマークを取得(`find_one()`)していない
        """
        if self.loaded_bookmark_dao is None:
            raise self.Error("Not loaded bookmark")

        bookmark_dao = self.loaded_bookmark_dao
        for k, v in bookmark.model_dump(exclude_none=True, exclude={"tags"}).items():
            setattr(bookmark_dao, k, v)

        self.bookmark_operator.save(bookmark_dao)
        self._save_tags(bookmark.tags, bookmark_dao.id)

    def _save_tags(self, tags: list[str] | None, bookmark_dao_id: int) -> None:
        """
        タグを保存し、ブックマークとタグの関連付けを行う。

        Args:
            tags: 保存するタグのリスト
            bookmark_dao_id: 関連付けるブックマークDAOのID
        """
        if tags is None:
            return
        # タグの保存
        self.tag_operator.save_by_names(tags)
        # ブックマークとタグの紐付け
        new_tags = self.tag_operator.find_by_names(tags)
        self.bookmark_tag_operator.save_by_tags(bookmark_dao_id, new_tags)

    def delete_one(self, /, hashed_id: str) -> None:
        """
        指定されたハッシュIDに対応するブックマークを削除する。

        Args:
            hashed_id: 削除対象のブックマークのハッシュID。

        Raises:
            NotFoundError: 指定されたハッシュIDに対応するデータが見つからない
        """
        bookmark_dao = self.bookmark_operator.find_one_by_hashed_id(hashed_id)
        if bookmark_dao is None:
            raise self.NotFoundError("Not found specified data.")

        self.bookmark_operator.delete(bookmark_dao)
