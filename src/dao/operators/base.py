from typing import Sequence, Type

from sqlalchemy import select
from sqlalchemy.orm.session import Session

from ..models.base import BaseDao


class BaseDaoOperator:
    """
    DAO操作クラス
    """

    MAIN_DAO: Type[BaseDao] = BaseDao

    def __init__(self, session: Session) -> None:
        """
        初期化

        :param session: セッション
        """
        self.session = session

    def find_one_by_id(self, id_value, id_column: str = "id"):
        """
        IDを指定して1レコード取得する。
        見つからない場合はNoneを返す。

        :param id_value: ID値
        :param id_column: IDカラム名
        :return: DAO or None
        """
        statement = select(self.MAIN_DAO).where(getattr(self.MAIN_DAO, id_column) == id_value)
        return self.session.execute(statement).scalars().one_or_none()

    def find_one_by_pkey(self, value):
        """
        主キーをを指定して1レコード取得する。
        見つからない場合はNoneを返す。

        :param value: 値
        :return: DAO or None
        """
        # id以外の主キーの場合は継承先のクラスでオーバーライドする
        return self.find_one_by_id(value)

    def find_all(self) -> list[BaseDao]:
        """
        全件取得する

        :return: DAOのリスト
        """
        statement = select(self.MAIN_DAO)
        return list(self.session.execute(statement).scalars().all())

    def save(
        self,
        d: BaseDao | Sequence[BaseDao],
    ) -> None:
        """
        指定されたDAOを保存する

        :param d: DAO or DAOのリスト・タプル
        :param session: セッション
        """

        def preprocess_insert_or_update(dao: BaseDao) -> None:
            """
            挿入や更新の前処理

            :param dao: DAO
            """
            if hasattr(dao, "created_at") and dao.created_at is None:
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
        指定されたDAOを削除する

        :param d: DAO or DAOのリスト・タプル
        :param session: セッション
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
