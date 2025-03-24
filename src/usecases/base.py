from typing import Type

from pydantic import BaseModel
from sqlalchemy.orm.session import Session


class UsecaseError(Exception):
    pass


class UsecaseBase:
    """
    ユースケース基底クラス
    """

    class Error(UsecaseError):
        pass

    def __init__(
        self,
        session: Session,
        response_model: Type[BaseModel],
    ):
        self.session = session
        self.response_model = response_model
