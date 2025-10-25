from typing import Sequence, Type

from sqlalchemy import Select, select
from sqlalchemy.orm.session import Session

from ...libs.page import Page
from ..models.base import BaseDao


class BaseDaoOperator:
    """
    DAO操作クラス
    """

    MAIN_DAO: Type[BaseDao] = BaseDao

    def __init__(
        self,
        session: Session,
        page: Page | None = None,
    ) -> None:
        """
        初期化処理

        Args:
            session: データベースセッション
            page: ページ情報
        """
        self.session = session
        self.page = page

    def find_one_by_id(self, id_value, id_column: str = "id"):
        """
        指定されたIDで1レコードを取得する。

        Args:
            id_value: 検索対象のID値
            id_column: 検索対象のIDカラム名。デフォルトは "id"

        Returns:
            取得したDAO、または見つからない場合はNone
        """
        statement = select(self.MAIN_DAO).where(getattr(self.MAIN_DAO, id_column) == id_value)
        return self.session.execute(statement).scalars().one_or_none()

    def find_one_by_pkey(self, value):
        """
        主キーを指定して1レコードを取得する。

        Args:
            value: 主キーの値

        Returns:
            取得したDAO、または見つからない場合はNone
        """
        # id以外の主キーの場合は継承先のクラスでオーバーライドする
        return self.find_one_by_id(value)

    def find_all(self) -> list[BaseDao]:
        """
        全件のレコードを取得する。

        Returns:
            取得したDAOのリスト
        """
        statement = select(self.MAIN_DAO)
        statement = self.pagenation(statement)
        return list(self.session.execute(statement).scalars().all())

    def pagenation(self, statement: Select) -> Select:
        """
        ページネーションを適用する。

        Args:
            statement: SQLAlchemyのクエリステートメント

        Returns:
            ページネーションを適用したクエリステートメント
        """
        if self.page:
            statement = statement.limit(self.page.size).offset(self.page.offset)
        return statement

    def save(self, d: BaseDao | Sequence[BaseDao]) -> None:
        """
        指定されたDAOを保存する。

        Args:
            d: 保存対象のDAO、またはDAOのリスト・タプル
        """

        def preprocess_insert_or_update(dao: BaseDao) -> None:
            """
            挿入や更新の前処理

            Args:
                dao: 対象のDAO
            """
            if hasattr(dao, "created_at") and getattr(dao, "created_at") is None:
                # 新規レコードをINSERT対象にする
                self.session.add(dao)

        if isinstance(d, Sequence):
            if not d:
                return
            # リスト・タプルの場合は要素ごとに処理する
            for dao in d:
                preprocess_insert_or_update(dao)
        else:
            preprocess_insert_or_update(d)
        # INSERT, UPDATE の実行
        self.session.flush()

    def delete(self, d: BaseDao | Sequence[BaseDao]) -> None:
        """
        指定されたDAOを削除する。

        Args:
            d: 削除対象のDAO、またはDAOのリスト・タプル
        """

        if isinstance(d, Sequence):
            if not d:
                return
            # リスト・タプルの場合は要素ごとに処理する
            for dao in d:
                self.session.delete(dao)
        else:
            self.session.delete(d)
        # DELETE の実行
        self.session.flush()
