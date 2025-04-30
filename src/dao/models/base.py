from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseDao(DeclarativeBase):
    """
    DAO基底クラス
    """

    def to_dict(self) -> dict:
        """
        属性を辞書型に変換する

        Returns:
            属性辞書
        """
        return dict([(k, v) for k, v in self.__dict__.items() if not k.startswith("_")])


# "CURRENT_TIMESTAMP" の略称
CT = "CURRENT_TIMESTAMP"


class TimeStampColumnMixin:
    """
    タイムスタンプカラムMixin
    """

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text(CT))
    "作成日時"
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text(CT), onupdate=text(CT)
    )
    "更新日時"
