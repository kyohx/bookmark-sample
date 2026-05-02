from ..dao.models.user import UserDao
from ..dao.operators.user import UserDaoOperator
from ..entities.user import UserEntity
from ..libs.cache import query_cache
from .base import BaseRepository


class UserRepository(BaseRepository):
    """
    ユーザリポジトリクラス
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_operator = UserDaoOperator(self.session, page=self.page)

    @query_cache(key_func=lambda self, name: type(self)._find_one_cache_key(name))
    def find_one(self, /, name: str) -> UserEntity:
        """
        指定されたユーザー名に対応するユーザーを1件取得する。

        Args:
            name: ユーザー名

        Returns:
            取得したユーザーエンティティ

        Raises:
            NotFoundError: 指定されたユーザー名に対応するデータが見つからない
        """
        user_dao = self.user_operator.find_one_by_name(name)
        if not user_dao:
            raise self.NotFoundError("Not found specified data.")

        return UserEntity(**user_dao.to_dict())

    @query_cache(key_func=lambda self: self._find_all_cache_key())
    def find_all(self) -> list[UserEntity]:
        """
        全てのユーザーを取得する。

        Returns:
            ユーザーエンティティのリスト
        """
        return [UserEntity(**user_dao.to_dict()) for user_dao in self.user_operator.find_all()]

    def add_one(self, user: UserEntity) -> None:
        """
        新しいユーザーを追加する。

        Args:
            user: 追加するユーザーエンティティ
        """
        user_dao = UserDao(**user.model_dump())

        self.user_operator.save(user_dao)
        # 詳細キーは直接削除し、一覧系は version を進めてまとめて無効化する。
        self._delete_cache_keys(type(self)._find_one_cache_key(user.name))
        self._bump_cache_versions("list")

    def update_one(self, user: UserEntity, /, current_name: str) -> None:
        """
        既存のユーザー情報を更新する。

        Args:
            user: 更新するユーザーエンティティ
            current_name: 更新対象の現在のユーザー名

        Raises:
            NotFoundError: 更新対象のユーザーが存在しない
        """
        user_dao = self.user_operator.find_one_by_name(current_name)
        if user_dao is None:
            raise self.NotFoundError("Not found specified data.")
        for k, v in user.model_dump(exclude_none=True).items():
            setattr(user_dao, k, v)

        self.user_operator.save(user_dao)
        # name 変更に備えて旧キーと新キーの両方を落とす。
        self._delete_cache_keys(
            type(self)._find_one_cache_key(current_name),
            type(self)._find_one_cache_key(user_dao.name),
        )
        self._bump_cache_versions("list")

    @staticmethod
    def _find_one_cache_key(name: str) -> str:
        return f"user:detail:{name}"

    def _find_all_cache_key(self) -> str:
        version = self._get_cache_version("list")
        return f"user:list:v:{version}:{self._page_cache_fragment()}"
