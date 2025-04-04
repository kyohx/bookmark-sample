from ..models.user import UserDao
from .base import BaseDaoOperator


class UserDaoOperator(BaseDaoOperator):
    """
    ユーザーDAO操作クラス
    """

    MAIN_DAO = UserDao

    def find_one_by_name(self, name: str) -> UserDao | None:
        """
        ユーザー名からを1件取得する
        """
        return super().find_one_by_id(name, id_column="name")
