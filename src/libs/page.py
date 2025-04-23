from pydantic import BaseModel, ConfigDict

from .constraints import FIELD_PAGE_NUMBER, FIELD_PAGE_SIZE


class Page(BaseModel):
    """
    ページ情報
    """

    number: FIELD_PAGE_NUMBER
    size: FIELD_PAGE_SIZE

    model_config = ConfigDict(frozen=True)

    def __init__(self, **data):
        super().__init__(**data)
        # SQLで使用するオフセットを計算しておく
        self._offset = (self.number - 1) * self.size

    @property
    def offset(self) -> int:
        return self._offset
