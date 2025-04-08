from fastapi import APIRouter

from ..dto.version import ResponseForGetVersion
from ..libs.version import APP_VERSION

router = APIRouter()


@router.get(
    "/version",
    response_model=ResponseForGetVersion,
    tags=["version"],
)
def get_version() -> ResponseForGetVersion:
    """
    バージョン番号取得
    """
    return ResponseForGetVersion(version=APP_VERSION)
