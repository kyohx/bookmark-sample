from ..models.user import UserDao
from .base import BaseDaoOperator


class UserDaoOperator(BaseDaoOperator):
    """
    ユーザーDAO操作クラス
    """

    MAIN_DAO = UserDao

    def find_one_by_name(self, name: str) -> UserDao | None:
        """
        ユーザー名からユーザーDAOを1件取得する。

        Args:
            name: 検索対象のユーザー名

        Returns:
            取得したユーザーDAO、または見つからない場合はNone
        """
        return super().find_one_by_id(name, id_column="name")
