from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseDao(DeclarativeBase):
    """
    DAO基底クラス
    """

    @property
    def tablename(self) -> str:
        """
        テーブル名を取得する

        :return: テーブル名
        """
        return self.__tablename__

    def to_dict(self) -> dict:
        """
        属性を辞書型に変換する

        :return: 属性辞書
        """
        return dict([(k, v) for k, v in self.__dict__.items() if not k.startswith("_")])

    def clone(self):
        """
        クローン作成

        :return: クローンしたDAOインスタンス
        """
        columns = dict(
            [
                (k, v)
                for k, v in self.to_dict().items()
                # クローン対象外の属性を除外
                if k not in ("id", "created_at", "updated_at")
            ]
        )
        return self.__class__(**columns)


# "CURRENT_TIMESTAMP" の略称
CT = "CURRENT_TIMESTAMP"


class TimeStampColumnMixin:
    """
    タイムスタンプカラムMixin
    """

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text(CT))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text(CT), onupdate=text(CT)
    )
