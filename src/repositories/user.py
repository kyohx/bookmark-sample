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
        self.user_operator = UserDaoOperator(self.session)
        self.loaded_user_dao: UserDao | None = None

    def find_one(self, /, name: str) -> UserEntity:
        """
        ユーザー1つを取得する
        """
        user_dao = self.user_operator.find_one_by_name(name)
        if not user_dao:
            raise self.NotFoundError("Not found specified data.")

        self.loaded_user_dao = user_dao

        return UserEntity(**user_dao.to_dict())

    def find_all(self) -> list[UserEntity]:
        """
        全ユーザーのリストを取得する
        """
        return [UserEntity(**user_dao.to_dict()) for user_dao in self.user_operator.find_all()]

    def add_one(self, user: UserEntity) -> None:
        """
        ユーザー情報を1件新規追加
        """
        user_dao = UserDao(**user.model_dump())

        self.user_operator.save(user_dao)

    def update_one(self, user: UserEntity) -> None:
        """
        ユーザー情報を1件更新

        事前に更新対象を find_one() で取得しておくこと
        """
        if self.loaded_user_dao is None:
            raise self.Error("Not loaded user")

        user_dao = self.loaded_user_dao
        for k, v in user.model_dump(exclude_none=True).items():
            setattr(user_dao, k, v)

        self.user_operator.save(user_dao)
