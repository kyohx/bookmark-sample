from ..dao.models.user import UserDao
from ..dao.operators.user import UserDaoOperator
from ..entities.user import UserEntity
from .base import BaseRepository


class UserRepository(BaseRepository):
    """
    ユーザリポジトリクラス
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_operator = UserDaoOperator(self.session, page=self.page)
        self.loaded_user_dao: UserDao | None = None

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
        if not user_dao or user_dao.disabled:
            raise self.NotFoundError("Not found specified data.")

        self.loaded_user_dao = user_dao

        return UserEntity(**user_dao.to_dict())

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

    def update_one(self, user: UserEntity) -> None:
        """
        既存のユーザー情報を更新する。

        事前に `find_one()` を使用して更新対象のユーザーを取得しておく必要がある。

        Args:
            user: 更新するユーザーエンティティ

        Raises:
            Error: 更新対象のユーザーを取得(`find_one()`)していない
        """
        if self.loaded_user_dao is None:
            raise self.Error("Not loaded user")

        user_dao = self.loaded_user_dao
        for k, v in user.model_dump(exclude_none=True).items():
            setattr(user_dao, k, v)

        self.user_operator.save(user_dao)
