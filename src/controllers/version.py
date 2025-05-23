from fastapi import APIRouter

from ..dto.version import ResponseForGetVersion
from ..libs.openapi_tags import TagNameEnum
from ..libs.version import APP_VERSION

router = APIRouter()
tagname = TagNameEnum.VERSION.value


@router.get(
    "/version",
    response_model=ResponseForGetVersion,
)
def get_version() -> ResponseForGetVersion:
    """
    バージョン番号取得
    """
    return ResponseForGetVersion(version=APP_VERSION)
