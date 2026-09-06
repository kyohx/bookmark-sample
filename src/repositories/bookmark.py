from urllib.parse import quote

from ..dao.models.bookmark import BookmarkDao
from ..dao.operators.bookmark import BookmarkDaoOperator
from ..dao.operators.bookmark_tag import BookmarkTagDaoOperator
from ..dao.operators.tag import TagDaoOperator
from ..entities.bookmark import BookmarkEntity
from ..libs.cache import query_cache
from .base import BaseRepository


class BookmarkRepository(BaseRepository):
    """
    ブックマークリポジトリクラス
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bookmark_operator = BookmarkDaoOperator(self.session, page=self.page)
        self.tag_operator = TagDaoOperator(self.session)
        self.bookmark_tag_operator = BookmarkTagDaoOperator(self.session)

    @query_cache(key_func=lambda self, hashed_id: type(self)._find_one_cache_key(hashed_id))
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

        # ループしない前提なのでn+1にはならない
        tags = self.tag_operator.find_by_bookmark_id(bookmark_dao.id)

        params = bookmark_dao.to_dict()
        params["tags"] = [tag.name for tag in tags]

        return BookmarkEntity(**params)

    @query_cache(key_func=lambda self: self._find_all_cache_key())
    def find_all(self) -> list[BookmarkEntity]:
        """
        全てのブックマークを取得する。

        Returns:
            ブックマークエンティティのリスト
        """
        bookmark_daos = self.bookmark_operator.find_all()
        return self._create_entities_with_tags(bookmark_daos)

    @query_cache(key_func=lambda self, tag_names: self._find_by_tags_cache_key(tag_names))
    def find_by_tags(self, tag_names: list[str]) -> list[BookmarkEntity]:
        """
        指定されたタグ名に関連付けられたブックマークを取得する。

        Args:
            tag_names: 検索対象のタグ名のリスト

        Returns:
            list[BookmarkEntity]: 指定されたタグに関連付けられたブックマークエンティティのリスト
        """
        bookmark_daos = self.bookmark_operator.find_by_tags(tag_names)
        return self._create_entities_with_tags(bookmark_daos)

    def _create_entities_with_tags(self, bookmark_daos: list[BookmarkDao]) -> list[BookmarkEntity]:
        """
        ブックマークDAOリストからタグ付きのエンティティを作成する。

        Args:
            bookmark_daos: ブックマークDAOのリスト

        Returns:
            タグ付きブックマークエンティティのリスト
        """
        if not bookmark_daos:
            return []

        bookmark_ids = [dao.id for dao in bookmark_daos]
        tags_rows = self.tag_operator.find_by_bookmark_ids(bookmark_ids)

        tags_map: dict[int, list[str]] = {dao_id: [] for dao_id in bookmark_ids}
        for bookmark_id, tag in tags_rows:
            tags_map[bookmark_id].append(tag.name)

        entities = []
        for dao in bookmark_daos:
            params = dao.to_dict()
            params["tags"] = tags_map.get(dao.id, [])
            entities.append(BookmarkEntity(**params))

        return entities

    def add_one(self, bookmark: BookmarkEntity) -> None:
        """
        新しいブックマークを追加する。

        Args:
            bookmark: 追加するブックマークエンティティ
        """
        bookmark_dao = BookmarkDao(**bookmark.model_dump(exclude={"tags"}))

        self.bookmark_operator.save(bookmark_dao)
        self.session.refresh(bookmark_dao)
        bookmark.created_at = bookmark_dao.created_at
        bookmark.updated_at = bookmark_dao.updated_at
        self._save_tags(bookmark.tags, bookmark_dao.id)
        # 詳細キーは直接削除し、一覧系は version を進めてまとめて無効化する。
        self._delete_cache_keys(type(self)._find_one_cache_key(bookmark_dao.hashed_id))
        self._bump_cache_versions("list", "tag-list")

    def update_one(self, bookmark: BookmarkEntity, /, current_hashed_id: str) -> None:
        """
        既存のブックマークを更新する。

        Args:
            bookmark: 更新するブックマークエンティティ
            current_hashed_id: 更新対象の現在のハッシュID

        Raises:
            NotFoundError: 更新対象のブックマークが存在しない
        """
        bookmark_dao = self.bookmark_operator.find_one_by_hashed_id(current_hashed_id)
        if bookmark_dao is None:
            raise self.NotFoundError("Not found specified data.")
        for k, v in bookmark.model_dump(exclude_none=True, exclude={"tags"}).items():
            setattr(bookmark_dao, k, v)

        self.bookmark_operator.save(bookmark_dao)
        self.session.refresh(bookmark_dao)
        bookmark.created_at = bookmark_dao.created_at
        bookmark.updated_at = bookmark_dao.updated_at
        self._save_tags(bookmark.tags, bookmark_dao.id)
        # ハッシュID変更にも耐えられるよう、旧キーと新キーの両方を削除する。
        self._delete_cache_keys(
            type(self)._find_one_cache_key(current_hashed_id),
            type(self)._find_one_cache_key(bookmark_dao.hashed_id),
        )
        self._bump_cache_versions("list", "tag-list")

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
        self._delete_cache_keys(type(self)._find_one_cache_key(hashed_id))
        self._bump_cache_versions("list", "tag-list")

    @staticmethod
    def _find_one_cache_key(hashed_id: str | None) -> str:
        return f"bookmark:detail:{hashed_id}"

    def _find_all_cache_key(self) -> str:
        version = self._get_cache_version("list")
        return f"bookmark:list:all:v:{version}:{self._page_cache_fragment()}"

    def _find_by_tags_cache_key(self, tag_names: list[str]) -> str:
        version = self._get_cache_version("tag-list")
        # タグ順や重複に依存しないように正規化し、区切り文字を含むタグでもキー衝突しないようにする。
        normalized_tags = ",".join(quote(tag_name, safe="") for tag_name in sorted(set(tag_names)))
        return f"bookmark:list:tags:{normalized_tags}:v:{version}:{self._page_cache_fragment()}"
